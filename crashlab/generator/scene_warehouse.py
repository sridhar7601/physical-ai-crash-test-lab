"""Photoreal warehouse scene: NVIDIA SimReady assets, same contract as scene.py.

Upgrades over the primitive scene, verified by probe before writing:

* The set is Isaac Sim's `warehouse_multiple_shelves.usd` — real shelving,
  pallets and floor markings, so occlusion context and clutter are genuine.
* The worker is the `male_adult_construction_01` character, whose hard hat is
  its own mesh (`...hardhat_01`). We label that mesh `hard_hat` and toggle its
  visibility per condition — the detector is asked about a genuinely WORN
  helmet, not a floating prop.
* Lighting buckets scale the environment's own lights (every light found on
  the stage) by target_lux / REFERENCE_LUX. Still uncalibrated — disclosed in
  the report — but monotonic and visually faithful to how a warehouse dims.

The per-frame contract (`apply(params, rng)`) matches `scene.py`, so
`generate.py` drives either scene unchanged.
"""

from __future__ import annotations

import math
import random

from .scene import (
    HAT_RADIUS_M,
    LOOK_AT_HEIGHT_M,
    FrameParameters,
    _SceneObject,
    _occluder_position,
)

#: Environment light scale of 1.0 is treated as this many lux — the render at
#: stock intensities reads as an ordinarily lit warehouse (probe: mean pixel
#: ~95/255). Uncalibrated proxy, recorded on every frame.
REFERENCE_LUX = 400.0

#: Cameras above this height clip into the roof structure; the achieved
#: elevation is recorded per frame whenever the clamp engages.
MAX_CAMERA_Z = 6.5

WORKER_USD = "/Isaac/People/Characters/original_male_adult_construction_01/male_adult_construction_01.usd"
WAREHOUSE_USD = "/Isaac/Environments/Simple_Warehouse/warehouse_multiple_shelves.usd"

#: Where the worker stands: an open stretch of aisle (probe-verified clear
#: sightlines toward -Y for 10+ metres).
WORKER_POS = (0.0, 0.0, 0.0)
HEAD_CENTRE = (0.0, 0.0, 1.72)  # hat centre on the character's head


def _apply_semantics(prim, label: str) -> str:
    """Label a prim for Replicator's annotators; returns which path worked."""
    try:
        from isaacsim.core.utils.semantics import add_update_semantics

        add_update_semantics(prim, label)
        return "isaacsim.core.utils.semantics"
    except Exception:
        pass
    try:
        from omni.isaac.core.utils.semantics import add_update_semantics

        add_update_semantics(prim, label)
        return "omni.isaac.core.utils.semantics"
    except Exception:
        pass
    # Manual application of the Semantics API attributes Replicator reads.
    from pxr import Sdf

    prim.ApplyAPI("SemanticsAPI", "Semantics")
    prim.CreateAttribute(
        "semantic:Semantics:params:semanticType", Sdf.ValueTypeNames.String
    ).Set("class")
    prim.CreateAttribute(
        "semantic:Semantics:params:semanticData", Sdf.ValueTypeNames.String
    ).Set(label)
    return "manual-usd-attributes"


class WarehouseSceneV2:
    """SimReady warehouse + construction worker, posed per scenario."""

    def __init__(self, resolution: tuple[int, int] = (1280, 720)) -> None:
        import omni.replicator.core as rep
        import omni.usd
        from pxr import Gf, Usd, UsdGeom

        try:
            from isaacsim.storage.native import get_assets_root_path
        except ImportError:
            from omni.isaac.nucleus import get_assets_root_path  # older releases

        self._rep = rep
        stage = omni.usd.get_context().get_stage()
        self._stage = stage
        root = get_assets_root_path()
        if not root:
            raise RuntimeError("no assets root: NVIDIA asset server unreachable")

        env = stage.DefinePrim("/World/Warehouse", "Xform")
        env.GetReferences().AddReference(root + WAREHOUSE_USD)

        worker = stage.DefinePrim("/World/Worker", "Xform")
        worker.GetReferences().AddReference(root + WORKER_USD)
        UsdGeom.XformCommonAPI(worker).SetTranslate(Gf.Vec3d(*WORKER_POS))

        # Let references, payloads and materials resolve before traversal.
        import omni.kit.app

        app = omni.kit.app.get_app()
        for _ in range(60):
            app.update()

        # --- find the hat mesh and label everything -----------------------
        hat_prim = None
        for prim in Usd.PrimRange(worker):
            if "hardhat" in prim.GetName().lower() and prim.GetTypeName() == "Mesh":
                hat_prim = prim
        if hat_prim is None:
            raise RuntimeError("worker character has no hardhat mesh; wrong asset?")

        via_hat = _apply_semantics(hat_prim, "hard_hat")
        via_person = _apply_semantics(worker, "person")
        print(f"[scene2] semantics: person via {via_person}, hard_hat via {via_hat}",
              flush=True)

        self.hat = _SceneObject(stage=stage, node=None,
                                paths=[hat_prim.GetPath().pathString])

        # --- inventory the environment's lights ---------------------------
        light_types = {"DomeLight", "DistantLight", "RectLight", "SphereLight",
                       "DiskLight", "CylinderLight"}
        self._lights: list[tuple[str, float]] = []
        for prim in stage.Traverse():
            if prim.GetTypeName() in light_types:
                attr = prim.GetAttribute("inputs:intensity") or prim.GetAttribute("intensity")
                if attr and attr.Get() is not None:
                    self._lights.append((prim.GetPath().pathString, float(attr.Get())))
        print(f"[scene2] controllable lights: {len(self._lights)}", flush=True)

        if not self._lights:
            # No stage lights: create one we own, so the lux factor still bites.
            dome = rep.create.light(light_type="dome", intensity=1000)
            for prim in stage.Traverse():
                if prim.GetTypeName() == "DomeLight":
                    self._lights.append((prim.GetPath().pathString, 1000.0))
            print("[scene2] no env lights found; created a dome", flush=True)

        # --- occluder (synthetic slab; occlusion is MEASURED, so honest) ---
        self.occluder = self._create(
            lambda: rep.create.cube(position=(0, -500, 0),
                                    scale=(HAT_RADIUS_M, 0.04, HAT_RADIUS_M * 1.5))
        )

        self.camera = self._create(
            lambda: rep.create.camera(position=(0, -6, 1.8),
                                      look_at=(0, 0, LOOK_AT_HEIGHT_M))
        )
        self.render_product = rep.create.render_product(self.camera.node, resolution)

    def _create(self, factory):
        before = {p.GetPath().pathString for p in self._stage.Traverse()}
        node = factory()
        after = {p.GetPath().pathString for p in self._stage.Traverse()}
        return _SceneObject(stage=self._stage, node=node,
                            paths=sorted(after - before, key=len))

    # ------------------------------------------------------------------

    def apply(self, params: FrameParameters, rng: random.Random) -> None:
        # Lighting: scale every stage light by the frame's lux factor.
        factor = max(0.01, params.target_lux / REFERENCE_LUX)
        for path, base in self._lights:
            prim = self._stage.GetPrimAtPath(path)
            if not prim.IsValid():
                continue
            attr = prim.GetAttribute("inputs:intensity") or prim.GetAttribute("intensity")
            if attr:
                attr.Set(base * factor)

        # Camera: same geometry as v1 but clamped under the roof. The frame
        # metadata records the pose actually used.
        x, y, z = params.camera_position
        clamped = z > MAX_CAMERA_Z
        if clamped:
            z = MAX_CAMERA_Z
        look_at = (WORKER_POS[0], WORKER_POS[1], LOOK_AT_HEIGHT_M)
        self.camera.look_from((WORKER_POS[0] + x, WORKER_POS[1] + y, z), look_at)
        params.camera_position = (WORKER_POS[0] + x, WORKER_POS[1] + y, z)

        # Helmet: toggle the WORN hat mesh; occlude with the slab when partial.
        self.hat.set_visible(params.hat_visible)
        if params.occluder_active and params.hat_visible:
            head = (WORKER_POS[0] + HEAD_CENTRE[0], WORKER_POS[1] + HEAD_CENTRE[1],
                    HEAD_CENTRE[2])
            self.occluder.set_translate(
                _occluder_position(head, params.camera_position,
                                   params.target_hat_visible_fraction)
            )
        else:
            self.occluder.set_translate((0.0, -500.0, 0.0))
        # Clutter: the warehouse provides it; the suite pins the factor anyway.
