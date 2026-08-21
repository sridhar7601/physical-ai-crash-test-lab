"""Warehouse scene construction and per-scenario physical parameters.

Runs inside Isaac Sim's Python only (imports `omni.*`). The rest of `crashlab`
stays free of simulator imports so it can be tested on a laptop.

Two design decisions worth stating, both learned by probing the live API:

* **Prims are tracked by diffing the stage**, not by guessing paths.
  `rep.create.cube()` produces a Mesh under an auto-named Xform, so searching
  by USD type name finds nothing. Snapshotting paths before and after each
  create call identifies exactly what it made, and cannot drift with the API.

* **Variation is applied directly through USD, not through Replicator's
  randomizers.** Each scenario needs one specific, reproducible scene derived
  from its own seed — not a random draw. Setting attributes and stepping is
  deterministic and, verified by probe, takes effect immediately. Randomizers
  under `rep.trigger.on_frame` are the documented path for random sampling and
  are precisely the wrong tool here: forget to register one and you silently
  render N identical frames.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Iterable

from ..schema import PHYSICAL_RANGES, Condition, Scenario

# --------------------------------------------------------------------------
# Physical mapping
# --------------------------------------------------------------------------

#: Distant-light intensity per target lux.
#:
#: UNCALIBRATED. Isaac's distant-light `intensity` is not in lux, and no
#: photometric calibration was performed. The scalar below is a monotonic
#: proxy chosen so the three lighting buckets are visually well separated
#: (probe: intensity 120 gave a mean pixel value of ~10/255; 3000 is daylight-
#: bright). Both the target lux and the applied intensity are recorded on every
#: frame, and the report carries this limitation explicitly. Do not present
#: bucket boundaries as calibrated illuminance measurements.
LUX_TO_INTENSITY = 2.5

WORKER_HEIGHT_M = 1.75
WORKER_RADIUS_M = 0.22
HAT_RADIUS_M = 0.16
HAT_THICKNESS_M = 0.07

#: Where the camera aims: the upper torso, so the head stays framed at all
#: distances and elevations.
LOOK_AT_HEIGHT_M = 1.35


def sample_in_bucket(factor: str, bucket: str, rng: random.Random) -> float:
    """Draw a concrete physical value from a bucket's declared range."""
    low, high = PHYSICAL_RANGES[factor]["buckets"][bucket]  # type: ignore[index]
    if low == high:
        return float(low)
    return rng.uniform(float(low), float(high))


@dataclass
class FrameParameters:
    """The concrete physical values used for one frame.

    Recorded alongside the image so a reader knows what "dim" meant in this
    specific frame, not just which bucket it belonged to.
    """

    scenario_id: str
    seed: int
    target_lux: float
    light_intensity: float
    camera_elevation_deg: float
    camera_azimuth_deg: float
    distance_m: float
    camera_position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    hat_visible: bool
    target_hat_visible_fraction: float
    occluder_active: bool
    clutter_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "target_lux": round(self.target_lux, 2),
            "light_intensity": round(self.light_intensity, 2),
            "light_intensity_is_calibrated": False,
            "camera_elevation_deg": round(self.camera_elevation_deg, 2),
            "camera_azimuth_deg": round(self.camera_azimuth_deg, 2),
            "distance_m": round(self.distance_m, 3),
            "camera_position": [round(v, 3) for v in self.camera_position],
            "look_at": [round(v, 3) for v in self.look_at],
            "hat_visible": self.hat_visible,
            "target_hat_visible_fraction": round(self.target_hat_visible_fraction, 3),
            "occluder_active": self.occluder_active,
            "clutter_count": self.clutter_count,
        }


def plan_frame(scenario: Scenario) -> FrameParameters:
    """Turn a scenario's buckets into concrete physical values.

    Pure arithmetic — no simulator involved — so it is unit-testable off-GPU,
    and driven entirely by the scenario's derived seed so the same scenario id
    always yields the same scene.
    """
    condition = scenario.condition
    rng = random.Random(scenario.seed)

    target_lux = sample_in_bucket("lighting", condition.lighting, rng)
    elevation = sample_in_bucket("camera_angle", condition.camera_angle, rng)
    distance = sample_in_bucket("distance", condition.distance, rng)
    visible_fraction = sample_in_bucket("helmet_state", condition.helmet_state, rng)
    clutter = int(round(sample_in_bucket("background_clutter", condition.background_clutter, rng)))

    # Azimuth is not a declared factor, so it varies freely: it stops every
    # frame in a bucket being the same photograph from the same spot, without
    # becoming an uncontrolled dimension of the experiment.
    azimuth = rng.uniform(-40.0, 40.0)

    elev_rad = math.radians(elevation)
    azim_rad = math.radians(azimuth)
    ground = distance * math.cos(elev_rad)
    height = LOOK_AT_HEIGHT_M + distance * math.sin(elev_rad)

    camera_position = (
        ground * math.sin(azim_rad),
        -ground * math.cos(azim_rad),
        height,
    )

    return FrameParameters(
        scenario_id=scenario.scenario_id,
        seed=scenario.seed,
        target_lux=target_lux,
        light_intensity=target_lux * LUX_TO_INTENSITY,
        camera_elevation_deg=elevation,
        camera_azimuth_deg=azimuth,
        distance_m=distance,
        camera_position=camera_position,
        look_at=(0.0, 0.0, LOOK_AT_HEIGHT_M),
        hat_visible=condition.helmet_present,
        target_hat_visible_fraction=visible_fraction,
        occluder_active=condition.helmet_state == "partial",
        clutter_count=clutter,
    )


# --------------------------------------------------------------------------
# Live scene (Isaac Sim only below this point)
# --------------------------------------------------------------------------


class WarehouseScene:
    """A minimal PPE scene, built once and re-posed for every frame.

    Rebuilding the stage per frame would be far slower and would defeat the
    warm shader cache, so the scene is constructed once and its prims are
    moved, hidden and re-lit per scenario.
    """

    MAX_CLUTTER = 20

    def __init__(self, resolution: tuple[int, int] = (1280, 720)) -> None:
        import omni.replicator.core as rep
        import omni.usd

        self._rep = rep
        self._stage = omni.usd.get_context().get_stage()

        self.floor = self._create(lambda: rep.create.plane(scale=20))
        self.worker = self._create(
            lambda: rep.create.cylinder(
                position=(0, 0, WORKER_HEIGHT_M / 2),
                scale=(WORKER_RADIUS_M, WORKER_RADIUS_M, WORKER_HEIGHT_M / 2),
                semantics=[("class", "person")],
            )
        )
        self.hat = self._create(
            lambda: rep.create.cube(
                position=(0, 0, WORKER_HEIGHT_M + HAT_THICKNESS_M / 2),
                scale=(HAT_RADIUS_M, HAT_RADIUS_M, HAT_THICKNESS_M),
                semantics=[("class", "hard_hat")],
            )
        )
        # Deliberately unlabelled: an occluder is scene furniture, not a class
        # the detector is asked to find. Parked far offstage when unused.
        #
        # Width matches the hat. An earlier version was ~3x wider, which buried
        # the helmet completely (measured occlusion 0.93) so the annotator
        # emitted no box at all — "partially occluded" silently became "absent".
        self.occluder = self._create(
            lambda: rep.create.cube(
                position=(0, -500, 0),
                scale=(HAT_RADIUS_M, 0.04, HAT_RADIUS_M * 1.5),
            )
        )
        self.clutter = [
            self._create(lambda: rep.create.cube(position=(0, -500, 0), scale=(0.4, 0.4, 0.4)))
            for _ in range(self.MAX_CLUTTER)
        ]
        self.light = self._create(
            lambda: rep.create.light(light_type="distant", intensity=1000)
        )
        self.camera = self._create(
            lambda: rep.create.camera(position=(0, -6, 2), look_at=(0, 0, LOOK_AT_HEIGHT_M))
        )

        self.render_product = rep.create.render_product(self.camera.node, resolution)

    # -- prim tracking ---------------------------------------------------

    def _create(self, factory):
        """Call a `rep.create.*` factory and capture the prims it produced.

        Diffing the stage is the only reliable way to learn what was created:
        the factories auto-name their prims and return graph nodes, not paths.
        """
        before = {p.GetPath().pathString for p in self._stage.Traverse()}
        node = factory()
        after = {p.GetPath().pathString for p in self._stage.Traverse()}
        new = sorted(after - before, key=len)
        return _SceneObject(stage=self._stage, node=node, paths=new)

    # -- per-frame application -------------------------------------------

    def apply(self, params: FrameParameters, rng: random.Random) -> None:
        """Pose the scene for one scenario."""
        self.light.set_attribute("inputs:intensity", params.light_intensity)
        self.camera.look_from(params.camera_position, params.look_at)

        hat_centre = (0.0, 0.0, WORKER_HEIGHT_M + HAT_THICKNESS_M / 2)
        self.hat.set_visible(params.hat_visible)

        if params.occluder_active and params.hat_visible:
            self.occluder.set_translate(
                _occluder_position(hat_centre, params.camera_position,
                                   params.target_hat_visible_fraction)
            )
        else:
            self.occluder.set_translate((0.0, -500.0, 0.0))

        for index, prim in enumerate(self.clutter):
            if index < params.clutter_count:
                angle = rng.uniform(0, 2 * math.pi)
                radius = rng.uniform(1.5, 7.0)
                prim.set_translate((radius * math.sin(angle), radius * math.cos(angle), 0.4))
            else:
                prim.set_translate((0.0, -500.0, 0.0))


def _occluder_position(
    hat_centre: tuple[float, float, float],
    camera_position: tuple[float, float, float],
    visible_fraction: float,
) -> tuple[float, float, float]:
    """Place a slab between camera and hat so it covers part of the hat.

    This is real occluding geometry on the real sightline — the helmet is
    genuinely hidden from the camera, not painted over in post. The exact
    fraction hidden is then *measured* from the renderer's `occlusionRatio`
    rather than assumed, so the bucket becomes verifiable ground truth.
    """
    hx, hy, hz = hat_centre
    cx, cy, cz = camera_position
    dx, dy, dz = cx - hx, cy - hy, cz - hz
    length = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    ux, uy, uz = dx / length, dy / length, dz / length

    # Sit close in front of the hat. The nearer the slab, the less perspective
    # magnifies it, so its own width — not the projection — governs coverage.
    standoff = 0.12
    px, py, pz = hx + ux * standoff, hy + uy * standoff, hz + uz * standoff

    # Slide sideways so a chosen fraction of the hat stays visible.
    #
    # `scale` on rep.create.cube sets TOTAL size, not half-extent, so a hat
    # created with scale=HAT_RADIUS_M spans +/-HAT_RADIUS_M/2 laterally. Both
    # hat and slab therefore have half-width h = HAT_RADIUS_M / 2.
    #
    # A slab centred at offset d covers from (d - h) up to +h, a width of
    # (2h - d), leaving visible fraction = d / 2h  ->  d = 2 * h * fraction
    #                                                    = HAT_RADIUS_M * fraction.
    #
    # An earlier version used 2 * HAT_RADIUS_M * fraction, i.e. twice this,
    # which slid the slab entirely clear of the helmet at eye level and close
    # range: measured occlusion 0.000 on ~5% of frames, and a median of 0.28
    # where the declared bucket implies 0.40-0.75.
    side_x, side_y = -uy, ux  # horizontal, perpendicular to the view direction
    offset = HAT_RADIUS_M * visible_fraction
    return (px + side_x * offset, py + side_y * offset, pz)


@dataclass
class _SceneObject:
    """A tracked set of prims created by one `rep.create.*` call."""

    stage: object
    node: object
    paths: list[str]

    def _prim(self, want_xformable: bool = True):
        from pxr import UsdGeom

        # The shallowest path is the Xform wrapper; transforms belong there.
        for path in self.paths:
            prim = self.stage.GetPrimAtPath(path)  # type: ignore[attr-defined]
            if not prim.IsValid():
                continue
            if not want_xformable or UsdGeom.Xformable(prim):
                return prim
        raise RuntimeError(f"no usable prim among {self.paths}")

    def set_translate(self, xyz: Iterable[float]) -> None:
        from pxr import Gf, UsdGeom

        prim = self._prim()
        xform = UsdGeom.Xformable(prim)
        for op in xform.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                op.Set(Gf.Vec3d(*xyz))
                return
        xform.AddTranslateOp().Set(Gf.Vec3d(*xyz))

    def set_visible(self, visible: bool) -> None:
        from pxr import UsdGeom

        for path in self.paths:
            prim = self.stage.GetPrimAtPath(path)  # type: ignore[attr-defined]
            if prim.IsValid() and UsdGeom.Imageable(prim):
                imageable = UsdGeom.Imageable(prim)
                if visible:
                    imageable.MakeVisible()
                else:
                    imageable.MakeInvisible()
                return

    def set_attribute(self, name: str, value: float) -> None:
        for path in self.paths:
            prim = self.stage.GetPrimAtPath(path)  # type: ignore[attr-defined]
            if not prim.IsValid():
                continue
            attr = prim.GetAttribute(name)
            if attr:
                attr.Set(float(value))
                return
        raise RuntimeError(f"attribute {name!r} not found on {self.paths}")

    def look_from(
        self, position: tuple[float, float, float], target: tuple[float, float, float]
    ) -> None:
        """Place the camera at `position` aimed at `target`.

        Sets a single transform matrix rather than Euler angles. Hand-rolled
        pitch/yaw needs the rotation order and handedness to be exactly right,
        and getting it wrong aims the camera at empty space — which renders
        blank frames that look like a broken model rather than a broken camera.
        A look-at basis has no such ambiguity.

        USD camera convention: looks along local -Z, +Y is up, +X is right.
        """
        from pxr import Gf, UsdGeom

        eye = Gf.Vec3d(*position)
        at = Gf.Vec3d(*target)
        world_up = Gf.Vec3d(0.0, 0.0, 1.0)  # Z-up stage

        z_axis = (eye - at).GetNormalized()          # camera's +Z points back
        x_axis = Gf.Cross(world_up, z_axis)
        if x_axis.GetLength() < 1e-6:
            # Looking straight up or down: any perpendicular will do.
            x_axis = Gf.Vec3d(1.0, 0.0, 0.0)
        x_axis = x_axis.GetNormalized()
        y_axis = Gf.Cross(z_axis, x_axis).GetNormalized()

        # USD uses row-vector convention: basis vectors are the rows.
        matrix = Gf.Matrix4d(
            x_axis[0], x_axis[1], x_axis[2], 0.0,
            y_axis[0], y_axis[1], y_axis[2], 0.0,
            z_axis[0], z_axis[1], z_axis[2], 0.0,
            eye[0], eye[1], eye[2], 1.0,
        )

        prim = self._prim()
        xform = UsdGeom.Xformable(prim)
        for op in xform.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                op.Set(matrix)
                return
        # Replace any pre-existing ops: mixing a translate op with a full
        # transform op would apply the offset twice.
        xform.SetXformOpOrder([])
        xform.AddTransformOp().Set(matrix)
