# Physical AI Site Planner

**Theme:** Physical AI with NVIDIA Omniverse

Warehouse safety cameras fail in predictable physical conditions — dim lighting, shelf occlusion, wrong mount angle. Staging those conditions in the real world is slow, expensive, and sometimes unsafe. Simulation reveals the blind spots; this product turns that knowledge into **actionable site guidance** before a single camera is mounted.

Physical AI Site Planner tells installers **where to place cameras** (height, angle, coverage) and tells floor managers **which zones are high-threat** (dim luminosity, occlusion, no coverage). Guidance is derived from simulation-measured failure patterns on the NVIDIA SimReady warehouse — the same lux, angle, and distance physics used in Isaac Sim.

The hackathon demo uses the `warehouse_multiple_shelves` environment. A 6×4 zone grid maps luminosity and occlusion risk; threat scores come from measured detection recall under dim + partial occlusion (17%) and high-angle + partial (24%). Six eye-level camera mounts are recommended; high-angle placements in dim corners are flagged as avoid.

Buyers are warehouse operators, manufacturing safety leaders, and site deployment engineers. Presidio can sell site surveys, Omniverse environment modelling, camera placement consulting, and recurring validation.

This prototype does not certify safety or replace on-site surveys. Its value is proactive guidance from simulation-measured physical conditions, not live camera feeds or object detection alone.
