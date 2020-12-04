import bpy

class AnimationSelectionPropertyGroup(bpy.types.PropertyGroup):
    """   """
    name: bpy.props.StringProperty(
        name = "Action Name",
        default = ""
    )
    
    isSelectedForExport: bpy.props.BoolProperty(
        name = "", # Force no name when rendering
        default = True
    )
    
    numFrames: bpy.props.IntProperty()

class MaterialSelectionPropertyGroup(bpy.types.PropertyGroup):
    """"""
    name: bpy.props.StringProperty(
        name = "Material",
        default = ""
    )

    index: bpy.props.IntProperty(
        name = "Index"
    )

    isSelectedForExport: bpy.props.BoolProperty(
        name = "", # Force no name when rendering
        default = True
    )

    role: bpy.props.EnumProperty(
        name = "",
        description = "How this material is used. Does not impact the rendered images, but is included in output metadata for import to other programs",
        items = [
            ("albedo", "Albedo/Base Color", "This material provides the albedo, or base color, of the object."),
            ("mask_unity", "Mask (Unity)", "This material is a Unity mask texture, where the red channel is metallic, green is occlusion, blue is the detail mask, and alpha is smoothness."),
            ("normal_unity", "Normal (Unity)", "This material is a normal map for use in Unity (tangent space, Y+)."),
            ("other", "Other", "Any use not fitting the options above.")
        ]
    )

def GetMaterialNameOptions(self, context):
    items = []

    for material in bpy.data.materials:
        items.append( (material.name, material.name, "") )

    return items

class ObjectMaterialPairPropertyGroup(bpy.types.PropertyGroup):
    materialName: bpy.props.EnumProperty(
        name = "Material Name",
        description = "TBD",
        items = GetMaterialNameOptions
        # TODO add change handler to set role based on material name (and preference to disable this)
    )

class MaterialSetPropertyGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name = "Set Name",
        description = "(Optional) A user-friendly name you can supply to help you keep track of your material sets"
    )

    role: bpy.props.EnumProperty(
        name = "Role",
        description = "How this material set is used. Does not impact the rendered images, but is included in output metadata for import to other programs",
        items = [
            ("albedo", "Albedo/Base Color", "This material provides the albedo, or base color, of the object."),
            ("mask_unity", "Mask (Unity)", "This material is a Unity mask texture, where the red channel is metallic, green is occlusion, blue is the detail mask, and alpha is smoothness."),
            ("normal_unity", "Normal (Unity)", "This material is a normal map for use in Unity (tangent space, Y+)."),
            ("other", "Other", "Any use not fitting the options above.")
        ]
    )

    objectMaterialPairs: bpy.props.CollectionProperty(type = ObjectMaterialPairPropertyGroup)

    selectedObjectMaterialPair: bpy.props.IntProperty(
        get = lambda self: -1 # dummy getter and no setter means items in the list can't be selected
    )

def GetCameraControlModeOptions(self, context):
    props = context.scene.SpritesheetPropertyGroup

    items = [
        ("move_once", "Fit All Frames", "The camera will be adjusted once before any rendering is done, so that the entire spritesheet is rendered from the same camera perspective.", 0),
        ("move_each_frame", "Fit Each Frame", "The camera will be adjusted before every render frame to fit the Target Object. Note that this will prevent the appearance of movement in the spritesheet.", 1)
    ]

    if props.useAnimations:
        items.append(("move_each_animation", "Fit Each Animation", "The camera will be adjusted at the start of each animation, so that the entire animation is rendered without subsequently moving the camera.", 2))

    if props.rotateObject:
        items.append(("move_each_rotation", "Fit Each Rotation", "The camera will be adjusted every time the Target Object is rotated, so that all frames for the rotation (including animations if enabled) are rendered without subsequently moving the camera.", 3))

    return items

def getCameraControlMode(self):
    val = self.get("cameraControlMode")

    if val is None:
        val = 0
    else:
        # Make sure the chosen value is still an option based on latest configuration
        items = GetCameraControlModeOptions(self, bpy.context)
        isValid = any(item[3] == val for item in items)

        if not isValid:
            val = 0 # default to moving once

    return val

def setCameraControlMode(self, value):
    self["cameraControlMode"] = value

class RenderTargetPropertyGroup(bpy.types.PropertyGroup):

    def onTargetObjectUpdated(self, context):
        # When selecting an object for the first time, auto-detect its associated material and assign it
        # in all of the material sets, for convenience
        if self.previousObject is None and self.object is not None and hasattr(self.object.data, "materials") and len(self.object.data.materials) > 0:
            props = context.scene.SpritesheetPropertyGroup
            
            # Figure out which index this object is, because it's the same in the material sets
            index = list(props.targetObjects).index(self)

            for materialSet in props.materialSets:
                materialSet.objectMaterialPairs[index].materialName = self.object.data.materials[0].name

        self.previousObject = self.object

    object: bpy.props.PointerProperty(
        name = "Render Target",
        description = "An object to be rendered into the spritesheet",
        type = bpy.types.Object,
        update = onTargetObjectUpdated
    )

    previousObject: bpy.props.PointerProperty(
        type = bpy.types.Object
    )

    rotationRoot: bpy.props.PointerProperty(
        name = "Rotation Root",
        description = "If 'Rotate Object' is set, this object will be rotated instead of the Render Target. This is useful for parent objects or armatures",
        type = bpy.types.Object
    )



class ReportingPropertyGroup(bpy.types.PropertyGroup):
    currentFrameNum: bpy.props.IntProperty() # which frame we are currently rendering

    elapsedTime: bpy.props.FloatProperty() # how much time has elapsed in the current job, in seconds

    hasAnyJobStarted: bpy.props.BoolProperty() # whether any job has started in the current session

    jobInProgress: bpy.props.BoolProperty() # whether a job is running right now

    lastErrorMessage: bpy.props.StringProperty() # the last error reported by a job (generally job-ending)

    outputDirectory: bpy.props.StringProperty() # the absolute path of the directory of the final spritesheet/JSON output

    suppressTerminalOutput: bpy.props.BoolProperty(
        name = "Suppress Terminal Output",
        description = "If true, render jobs will not print anything to the system console (stdout)",
        default = True
    )

    systemType: bpy.props.EnumProperty( # what kind of file explorer is available on this system
        items = [
            ("unchecked",  "", ""),
            ("unknown", "", ""),
            ("windows", "", "")
        ]
    )

    totalNumFrames: bpy.props.IntProperty() # the total number of frames which will be rendered

    def estimatedTimeRemaining(self):
        if self.currentFrameNum == 0 or self.totalNumFrames == 0:
            return None

        # This isn't fully accurate since we have some time-consuming tasks regardless of the number of
        # frames, but render time is the vast majority of any substantial job, so close enough
        timePerFrame = self.elapsedTime / self.currentFrameNum
        return (self.totalNumFrames - self.currentFrameNum) * timePerFrame

class SpritesheetPropertyGroup(bpy.types.PropertyGroup):
    """Property group for spritesheet rendering configuration"""

    #### Animation data
    activeAnimationSelectionIndex: bpy.props.IntProperty()

    animationSelections: bpy.props.CollectionProperty(type = AnimationSelectionPropertyGroup)

    outputFrameRate: bpy.props.IntProperty(
        name = "Output Frame Rate",
        description = "The frame rate of the animation in the spritesheet",
        default = 24,
        min = 1
    )

    useAnimations: bpy.props.BoolProperty(
        name = "Animate During Render",
        description = "If true, the Target Object will be animated during rendering",
        default = True
    )

    ### Materials data
    activeMaterialSelectionIndex: bpy.props.IntProperty()
    
    materialSelections: bpy.props.CollectionProperty(type = MaterialSelectionPropertyGroup)

    materialSets: bpy.props.CollectionProperty(type = MaterialSetPropertyGroup)

    selectedMaterialSetIndex: bpy.props.IntProperty()

    useMaterials: bpy.props.BoolProperty(
        name = "Render Multiple Materials",
        description = "If true, the target object will be rendered once for each selected material",
        default = True
    )
    
    ### Render properties
    controlCamera: bpy.props.BoolProperty(
        name = "Control Camera",
        description = "If true, the Render Camera will be moved and adjusted to best fit the Target Object in view",
        default = True
    )

    cameraControlMode: bpy.props.EnumProperty(
        name = "",
        description = "How to control the Render Camera",
        items = GetCameraControlModeOptions,
        get = getCameraControlMode,
        set = setCameraControlMode
    )

    padToPowerOfTwo: bpy.props.BoolProperty(
        name = "Pad to Power-of-Two",
        description = "If true, all output images will be padded with transparent pixels to the smallest power-of-two size that can fit the original output",
        default = True
    )

    rotateObject: bpy.props.BoolProperty(
        name = "Rotate Objects",
        description = "Whether to rotate the target objects. All objects will be rotated simultaneously, but you may choose an object to rotate each around (such as a parent or armature)"
    )
    
    rotationNumber: bpy.props.IntProperty(
        name = "Total Angles",
        description = "How many rotations to perform",
        default = 8,
        min = 2
    )

    rotationRoot: bpy.props.PointerProperty(
        name = "",
        description = "Which object to apply rotation to, useful e.g. with armatures. If left empty, rotations will be applied to Target Object",
        type = bpy.types.Object
    )
    
    spriteSize: bpy.props.IntVectorProperty(
        name = "Sprite Size",
        description = "How large each individual sprite should be",
        default = (64, 64),
        min = 16,
        size = 2
    )

    ### Scene properties
    renderCamera: bpy.props.PointerProperty(
        name = "Render Camera",
        description = "The camera to use for rendering; defaults to the scene's camera if unset",
        type = bpy.types.Object
    )

    targetObject: bpy.props.PointerProperty(
        name = "Target Object",
        description = "The object which will be animated and rendered into the spritesheet",
        type = bpy.types.Object
    )

    targetObjects: bpy.props.CollectionProperty(
        name = "Render Targets",
        type = RenderTargetPropertyGroup
    )

    selectedTargetObjectIndex: bpy.props.IntProperty()

    ### Output file properties
    separateFilesPerAnimation: bpy.props.BoolProperty(
        name = "Separate Files Per Animation",
        description = "If 'Control Animations' is enabled, this will generate one output file per animation action. Otherwise, all actions will be combined in a single file",
        default = False
    )

    separateFilesPerMaterial: bpy.props.BoolProperty(
        name = "Separate Files Per Material Set",
        description = "If 'Control Materials' is enabled, this will generate one output file per material set. This cannot be disabled",
        default = True
    )

    separateFilesPerRotation: bpy.props.BoolProperty(
        name = "Separate Files Per Rotation",
        description = "If 'Rotate During Render' is enabled, this will generate one output file per rotation option",
        default = False
    )
