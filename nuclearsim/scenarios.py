"""Scenario definitions and severity descriptors for NuclearSim.

Each scenario has:
  - prompt: the base video prompt (camera, environment, style).
  - environment: short tag for downstream code and filenames.
  - task: what the robot is trying to learn to do.
  - complexity: "single" (one defect type) or "compound" (multiple hazards).
  - expected_defects: defect classes the VLM is likely to see.

Severity descriptors (1 = pristine, 5 = catastrophic) are concatenated onto
the base prompt at generation time so the video physically matches the
requested severity level.
"""

SCENARIOS = {
    # -----------------------------------------------------------------------
    "pipe_crack": {
        "prompt": (
            "Photorealistic first-person point-of-view from a small "
            "inspection robot crawler moving slowly forward inside a dark, "
            "narrow cylindrical steel industrial pipe approximately 30 "
            "centimeters in diameter. The only light source is a bright "
            "forward-facing flashlight mounted on the robot that illuminates "
            "the curved pipe walls ahead, casting soft falloff and long "
            "shadows. The metal surface has realistic brushed-steel "
            "texture with subtle scratches and weld seams. Cold, "
            "industrial, claustrophobic atmosphere. No humans anywhere in "
            "frame. Cinematic realism, 16:9."
        ),
        "environment": "pipe_interior_steel",
        "task": "crack_detection",
        "complexity": "single",
        "expected_defects": ["crack", "corrosion"],
    },

    # -----------------------------------------------------------------------
    "flooded_basement": {
        "prompt": (
            "Photorealistic first-person point-of-view from an inspection "
            "robot moving slowly through a flooded industrial basement "
            "inside a nuclear power facility. Concrete walls and floors, "
            "exposed pipework running along the ceiling, electrical panels "
            "and conduit boxes mounted on the walls. Flickering, failing "
            "fluorescent emergency lights overhead cast intermittent blue-"
            "green highlights that reflect off the water's surface. Visible "
            "ripples radiate from the robot's movement. Cold, hazardous, "
            "abandoned feel. No humans anywhere in frame. Cinematic "
            "realism, 16:9."
        ),
        "environment": "basement_flooded",
        "task": "flood_hazard_assessment",
        "complexity": "single",
        "expected_defects": ["flood_hazard"],
    },

    # -----------------------------------------------------------------------
    "gauge_anomaly": {
        "prompt": (
            "Photorealistic first-person point-of-view from an inspection "
            "robot rolling slowly down a narrow nuclear power plant "
            "corridor. Painted concrete walls, metal grating floor, "
            "horizontal runs of industrial steel piping, and multiple "
            "circular analog pressure gauges mounted at chest height on "
            "both the left and right walls. Each gauge has a clear glass "
            "face, black numerals, a green safe zone, a yellow warning "
            "zone, and a red danger zone. Harsh overhead fluorescent "
            "lighting produces sharp shadows and specular highlights on "
            "the metal surfaces. No humans anywhere in frame. Cinematic "
            "realism, 16:9."
        ),
        "environment": "plant_corridor",
        "task": "anomaly_detection",
        "complexity": "single",
        "expected_defects": ["gauge_anomaly"],
    },

    # -----------------------------------------------------------------------
    "corridor_multiple_hazards": {
        "prompt": (
            "Photorealistic first-person point-of-view from an inspection "
            "robot moving slowly down a dim nuclear power plant corridor "
            "that contains several independent hazards simultaneously. "
            "Painted concrete walls, metal grating floor, horizontal "
            "runs of industrial pipes with insulation wrapping, and "
            "circular pressure gauges mounted on both walls. Overhead "
            "fluorescent lights are failing and flicker intermittently. "
            "The scene mixes structural, fluid, and instrumentation "
            "anomalies in the same frame. No humans anywhere in frame. "
            "Cinematic realism, 16:9."
        ),
        "environment": "plant_corridor_compound",
        "task": "compound_hazard_assessment",
        "complexity": "compound",
        "expected_defects": [
            "gauge_anomaly",
            "flood_hazard",
            "structural_damage",
        ],
    },
}


SEVERITY_DESCRIPTORS = {
    # -----------------------------------------------------------------------
    "pipe_crack": {
        1: (
            "The pipe wall is pristine: uniform metallic surface, no cracks, "
            "no rust, no discoloration. Clean factory-new condition."
        ),
        2: (
            "The pipe wall shows only minor cosmetic wear: a few faint "
            "surface scratches, no rust, no cracks. Barely visible even "
            "under direct flashlight."
        ),
        3: (
            "A single hairline crack roughly three centimeters long runs "
            "along the pipe wall at the two-o'clock position. A patch of "
            "light orange surface rust spreads about two centimeters "
            "outward from the crack. Defect is clearly visible but "
            "contained."
        ),
        4: (
            "A prominent crack roughly eight centimeters long runs along "
            "the pipe wall at the two-o'clock position. Deep orange-red "
            "corrosion penetrates into the metal around the crack, and "
            "the pipe wall shows visible deformation and pitting near "
            "the defect. Serious structural concern."
        ),
        5: (
            "Catastrophic fracture: the pipe wall is partially separated "
            "along a long jagged crack. Heavy black-and-orange corrosion "
            "surrounds the failure. Fluid seepage and wet streaks run "
            "down the pipe wall from the break. Pipe is effectively "
            "compromised."
        ),
    },

    # -----------------------------------------------------------------------
    "flooded_basement": {
        1: (
            "The basement floor is completely dry. All equipment is dry "
            "and undisturbed. No water anywhere. Baseline clean scene."
        ),
        2: (
            "Shallow puddles roughly two centimeters deep are scattered "
            "across the floor. Minor moisture visible on walls. Equipment "
            "is still dry. Early warning stage."
        ),
        3: (
            "Murky brown water has flooded the floor to a depth of about "
            "twenty centimeters. The lower portions of electrical panels "
            "and piping are submerged. Water ripples visibly from the "
            "robot's movement."
        ),
        4: (
            "Murky brown water has flooded the room to a depth of about "
            "forty centimeters. Electrical panels and horizontal pipe "
            "runs are substantially submerged. Flickering emergency "
            "lights reflect chaotically off the water surface. Hazardous "
            "conditions."
        ),
        5: (
            "Deep flood roughly eighty centimeters deep submerges almost "
            "all equipment. Floating debris drifts on the surface. A "
            "partially submerged electrical panel sparks intermittently. "
            "An oil sheen swirls across the water. Immediate evacuation "
            "conditions."
        ),
    },

    # -----------------------------------------------------------------------
    "gauge_anomaly": {
        1: (
            "Every visible gauge on both walls reads within the green "
            "safe zone. Needles are steady near the center of normal "
            "operating range. All instrumentation nominal."
        ),
        2: (
            "One gauge on the right wall has its needle resting exactly "
            "on the boundary between the green safe zone and the yellow "
            "warning zone. All other gauges remain in the green safe "
            "zone. Early-stage drift."
        ),
        3: (
            "One prominent gauge on the right wall shows its needle "
            "clearly inside the yellow warning zone, about twenty percent "
            "past the safe operating limit. Remaining gauges are green. "
            "Monitoring required."
        ),
        4: (
            "One prominent gauge on the right wall has its needle deep "
            "inside the red danger zone, well past the warning line. The "
            "needle is pinned hard against the high end of the scale. "
            "Other gauges are still green but the contrast is dramatic. "
            "Immediate operator alert warranted."
        ),
        5: (
            "Multiple gauges on both walls are pinned deep in the red "
            "danger zone. One gauge has a visibly cracked glass face. "
            "Overhead lighting has switched to pulsing red emergency "
            "illumination. Plant is in alarm state."
        ),
    },

    # -----------------------------------------------------------------------
    "corridor_multiple_hazards": {
        1: (
            "Corridor is clean and dry. All gauges read green. Lighting "
            "is steady. No visible hazards anywhere. Baseline scene."
        ),
        2: (
            "One gauge on the right wall reads yellow at the warning "
            "boundary. A small damp patch is visible on the floor under "
            "a ceiling pipe. One overhead fluorescent light flickers "
            "occasionally. Early composite warning signs."
        ),
        3: (
            "One gauge on the right wall reads clearly in the red danger "
            "zone. Water is pooling on the floor from a slow leak at a "
            "ceiling pipe junction. A section of pipe insulation on the "
            "left wall is visibly damaged and partially torn. Multiple "
            "concurrent anomalies."
        ),
        4: (
            "One large pressure gauge on the right wall has its needle "
            "pinned deep in the red danger zone. Water is pooling on the "
            "floor to a depth of roughly fifteen centimeters from an "
            "active ceiling leak. A long section of pipe insulation on "
            "the left wall is torn loose and hanging down. Emergency "
            "lights flicker visibly. Serious composite hazard."
        ),
        5: (
            "Multiple gauges on both walls are pinned in the red danger "
            "zone. Heavy flooding roughly forty centimeters deep covers "
            "the corridor floor. A large section of pipe insulation has "
            "collapsed into the water. A wall-mounted electrical panel "
            "sparks visibly. Overhead emergency strobe lights pulse red. "
            "Full evacuation conditions."
        ),
    },
}
