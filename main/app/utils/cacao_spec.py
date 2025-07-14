PLAYBOOK_NAME_DESCRIPTION = """
    A name for this playbook. Playbook names often follow naming  convention that is unique within an organization, community, or  trust group and as such this name SHOULD be unique.
"""

PLAYBOOK_DESCRIPTION_DESCRIPTION = """
    More details, context, and possibly an explanation about what this playbook does and tries to accomplish.
"""

PLAYBOOK_TYPES_DESCRIPTION = """
    A list of playbook types that specifies the operational roles that this playbook addresses. This property SHOULD be populated. The values for this property SHOULD come from the playbook-type-ov vocabulary (see section 3.1.1).
    3.1.1 Playbook Type Vocabulary
    A playbook may be categorized as having multiple types defined from this vocabulary.
    
    'attack' - Attack Playbook: A playbook that is primarily focused on the orchestration steps required to execute a penetration test or perform adversarial emulation. These playbooks can help an organization test and verify the security controls in a specific environment and potentially identify vulnerabilities or other changes necessary to improve defensive posture within that environment. For example, an attack playbook can contain the specific actions that a red-team should perform that are within the scope and rules of engagement for a specific penetration test. An attack playbook may also be used to capture, in a structured way, the sequence of an adversary's behavior as described in a text-based cyber threat intelligence (CTI) report.
    
    'detection' - Detection Playbook: A playbook that is primarily focused on the orchestration steps required to detect a known security event, known or expected security-relevant activity, or for threat hunting. For example, a detection playbook can contain the actions needed to help organizations detect a specific attack or campaign.
    
    'engagement' - Engagement Playbook: A playbook that is primarily focused on the orchestration steps required to engage in denial, deception, strategic planning, and analysis activity to support adversary engagement. Whereas attack playbooks leverage actions against known defenders to test an environment, engagement playbooks define actions and countermeasures against adversaries to increase their cost to operate and decrease the value of their operations. For example, an engagement playbook can contain the actions needed to provide misinformation about data or systems to decrease the value an adversary places on the assets, or it can contain the actions needed to disrupt network access to increase the adversary’s operational costs.
    
    'investigation' - Investigation Playbook: A playbook that is primarily focused on the orchestration steps required to investigate what affects a security event, incident, or other security-relevant activity has caused. Investigation playbooks will likely inform other subsequent actions upon completion of the investigation. For example, an investigation playbook can contain the actions needed to check various systems for suspicious activity.
    
    'mitigation' - Mitigation Playbook: A playbook that is primarily focused on the orchestration steps required to mitigate a security event or incident that has occurred when remediation is not initially possible. Organizations often choose to mitigate a security event or incident until they can actually remediate it. Mitigation playbooks are designed to reduce or limit the impact of suspicious or confirmed malicious activity. For example, a mitigation playbook can contain the specific actions to be used to quarantine affected users/devices/applications from the network temporarily to prevent additional problems. Mitigation usually precedes remediation, after which the mitigation actions are reversed.
    
    'notification' - Notification Playbook: A playbook that is primarily focused on the orchestration steps required to notify and disseminate information and other playbooks about a security event, incident, or threat. For example, a notification playbook can be used to notify multiple entities about a new attack or campaign and disseminate information or playbooks to deal with it as quickly as possible.
    
    'prevention' - Prevention Playbook: A playbook that is primarily focused on the orchestration steps required to prevent a known or expected security event, incident, or threat from occurring. Prevention playbooks are often designed and deployed as part of best practices to safeguard organizations from known and perceived threats and behaviors associated with suspicious activity. For example, a prevention playbook can contain the specific actions that need to be deployed on certain systems to prevent a new attack or campaign.

    'remediation' - Remediation Playbook: A playbook that is primarily focused on the orchestration steps required to remediate, resolve, or fix the resultant state of a security event or incident and return the system, device, or network back to a nominal operating state. Remediation playbooks can fix affected assets by selectively correcting problems due to malicious activity by reverting the system or network to a known good state. For example, a remediation playbook can contain the specific actions that need to be deployed to ensure that a system or device is no longer infected with some malware. If mitigation steps were previously applied, they might need to be undone during remediation; however, this is all implementation specific and dependent on how the playbooks were created and executed.
"""

PLAYBOOK_TYPES_VALID = [
    "attack",
    "detection",
    "engagement",
    "investigation",
    "mitigation",
    "notification",
    "prevention",
    "remediation",
]

PLAYBOOK_ACTIVITIES_DESCRIPTION = """
    A list of activities pertaining to the playbook. This property SHOULD be populated. If the playbook_types property is populated and comes from the playbook-type-ov then this property MUST have at least one assigned activity.
    This property allows an author to define more detailed descriptions for the various activities that a playbook performs. This property provides a much richer and verbose method to describe all aspects of a playbook than just the playbook_types property.

    The values for this property SHOULD come from the playbook-activity-type-ov vocabulary (see section 3.1.2).
    Each listed activity MUST be reflected in a CACAO workflow step object and that object MUST be included in the workflow property.

    3.1.2 Playbook Activity Type Vocabulary 
    Playbook activity differs according to playbook type. Activity type values and descriptions are given below, organized by playbook type: Notification (N), Detection (D), Investigation (I), Prevention (P), Mitigation (M), Remediation (R), Attack (A), Engagement (E). Required activities (indicated by M’s) in bold face font) uniquely identify a playbook type and MUST be defined; optional activities SHOULD (indicated by S’s) or MAY (indicated by O’s) be associated with one or more playbook types.

    'compose-content' - This activity composes the notification text that will be distributed. This activity MUST be used with notification playbooks.

    'deliver-content' - This activity delivers notification content to the intended audience. This activity SHOULD be used with notification playbooks.

    'identify-audience' - This activity identifies the audience of a notification. This activity SHOULD be used with notification playbooks.

    'identify-channel' - This activity identifies the method by which notification content will be sent. This activity SHOULD be used with notification playbooks.

    'scan-system' - This activity scans a system (workstation, server, network device) to identify potential compromises. This activity SHOULD be used with detection, investigation, and mitigation playbooks.
    
    'match-indicator' - This activity matches on an indicator through traffic monitoring, system scans, and log analysis. This activity MUST be used with detection playbooks.
    
    'analyze-collected-data' - This activity analyzes historical output from security devices (e.g., logs and network traffic capture). This activity SHOULD be used with investigation playbooks.
    
    'identify-indicators' - This activity identifies one or more indicators that can be used to detect a security event. This activity MUST be used with investigation playbooks.
    
    'scan-vulnerabilities' - This activity identifies vulnerabilities of a system. This activity SHOULD be used with prevention playbooks and MAY be used with attack playbooks.
    
    'configure-systems' - This activity confirms secure configuration and if necessary, updates or configures systems or security devices to be resistant to a security event. This activity MUST be used with prevention playbooks.
    
    'restrict-access' - This activity blocks applications and network traffic (ports/IP addresses/URLs) to mitigate a security event This activity SHOULD be used with mitigation playbooks.
    
    'disconnect-system' - This activity disconnects a compromised system from the network. This activity MAY be used with mitigation playbooks.
    
    'eliminate-risk' - This activity eliminates the risk that a threat will affect a network by restricting capabilities. This activity MUST be used with mitigation playbooks.
    
    'revert-system' - This activity reimages a system returning it to a known- good state. This activity MAY be used with remediation playbooks.
    
    'restore-data' - This activity restores data after a compromise (e.g., ransomware). This activity MAY be used with remediation playbooks.
    
    'restore-capabilities' - This activity restarts services and opens network access. This activity MUST be used with remediation playbooks.
    
    'map-network' - This activity maps a network to identify components that may be subject to compromise and to ensure the environment meets requirements for subsequent actions, such as a penetration test or attack simulation. This activity MAY be used with attack playbooks.
    
    'identify-steps' - This activity identifies steps (tactics, techniques, and protocols) for use in a penetration test, attack simulation, or adversary emulation plan. These steps will become the step sequence. This activity MAY be used with attack playbooks (alternatively, an attack playbook may comprise only the steps pertaining to the operation).
    
    'step-sequence' - This activity is a sequence of TTPs or steps that represents an adversary emulation plan, penetration test, or attack simulation. This activity MUST be used with attack playbooks.
    prepare-engagement - This activity identifies what the defender wants to accomplish with respect to engaging (and misleading) an adversary and determines and aligns an operation with a desired end-state. This activity MUST be used with engagement playbooks.
    
    'execute-operation' - This activity implements and deploys denial and deception activities designed for adversary engagement. This activity MUST be used with engagement playbooks.
    
    'analyze-engagement-results' - This activity turns operational engagement outputs into actionable intelligence. Assessment of the intelligence enables capture of lessons learned and refinement of future adversary engagements. This activity MUST be used with engagement playbooks.
"""

PLAYBOOK_ACTIVITIES_VALID = [
    "compose_content",
    "deliver_content",
    "identify_audience",
    "identify-channel",
    "scan-system",
    "match-indicator",
    "analyze-collected-data",
    "identify-indicators",
    "scan-vulnerabilities",
    "configure-systems",
    "restrict-access",
    "disconnect-system",
    "eliminate-risk",
    "revert-system",
    "restore-data",
    "restore-capabilities",
    "map-network",
    "identify-steps",
    "step-sequence",
    "prepare-engagement",
    "execute-operation",
    "analyze-engagement-results",
]

PLAYBOOK_LABELS_DESCRIPTION = """
    A set of terms, labels, or tags associated with this playbook. The values may be user, organization, or trust-group defined and their meaning is outside the scope of this specification.
"""

PLAYBOOK_CREATED_DESCRIPTION = """
    The time at which this playbook was originally created. The creator can use any time it deems most appropriate as the time the playbook was created, but it MUST be given to the nearest millisecond (exactly three digits after the decimal place in seconds). The created property MUST NOT be changed when creating a new version of the object.

    The timestamp data type represents dates and times and uses the JSON string type [RFC8259] for serialization. The timestamp data MUST be a valid RFC 3339-formatted timestamp [RFC3339] using the format yyyy-mm-ddThh:mm:ss[.s+]Z where the "s+" represents 1 or more sub-second values. The brackets denote that sub-second precision is optional, and that if no digits are provided, the decimal place MUST NOT be present. The timestamp MUST be represented in the UTC+0 timezone and MUST use the "Z" designation to indicate this. Additional requirements may be defined where this data type is used.
"""

PLAYBOOK_MODIFIED_DESCRIPTION = """
    The time that this particular version of the playbook was last modified. The creator can use any time it deems most appropriate as the time that this version of the playbook was modified, but it MUST be given to the nearest millisecond (exactly three digits after the decimal place in seconds). The modified property MUST be later than or equal to the value of the created property. If created and modified properties are the same, then this is the first version of the playbook.

    The timestamp data type represents dates and times and uses the JSON string type [RFC8259] for serialization. The timestamp data MUST be a valid RFC 3339-formatted timestamp [RFC3339] using the format yyyy-mm-ddThh:mm:ss[.s+]Z where the "s+" represents 1 or more sub-second values. The brackets denote that sub-second precision is optional, and that if no digits are provided, the decimal place MUST NOT be present. The timestamp MUST be represented in the UTC+0 timezone and MUST use the "Z" designation to indicate this. Additional requirements may be defined where this data type is used.
"""

WORKFLOW_DESCRIPTION = """
    Workflows contain a series of steps that are stored in a dictionary (see the workflow property in section
    3.1), where the key is the step ID and the value is a workflow step. These workflow steps along with the
    associated commands form the building blocks for playbooks and are used to control the commands that
    need to be executed. Workflows steps are processed either sequentially, in parallel, or both depending on
    the type of steps required by the playbook. In addition to simple processing, workflow steps MAY also
    contain conditional and/or temporal operations to control the execution of the playbook.
    Conditional processing means executing steps or commands after some sort of condition is met.
    Temporal processing means executing steps or commands either during a certain time window or after
    some period of time has passed.
"""

WORKFLOW_STEP_TYPES_VALID = [
    "start",
    "end",
    "action",
    "playbook-action",
    "parallel",
    "if-condition",
    "while-condition",
    "switch-condition",
]


WORKFLOW_STEP_NAMES_DESCRIPTION = """
    A name for this step that is meant to be displayed in a user interface or captured in a log message.
"""

WORKFLOW_STEP_DESCRIPTION_DESCRIPTION = """
    More details, context, and possibly an explanation about what this step does and tries to accomplish.
"""


WORKFLOW_STEP_PARALLEL_DESCRIPTION = """
    4.7 Parallel Step
    The parallel step workflow step defines how to create steps that are processed in parallel. This workflow step allows playbook authors to define two or more steps that can be executed at the same time. For example, a playbook that responds to an incident may require both the network team and the desktop team to investigate and respond to a threat at the same time. Another example is a response to a cyber attack on an operational technology (OT) environment that requires releasing air / steam / water pressure simultaneously. In addition to the inherited properties, this section defines the following additional property that is valid for this type. Implementations MUST wait for all steps referenced in the next_steps property to complete before moving on.
    The steps referenced from this object are intended to be processed in parallel, however, if an implementation cannot support executing steps in parallel, then the steps MAY be executed in sequential order if the desired outcome is the same.
"""
WORKFLOW_STEP_PARALLEL_PROPERTIES_DESCRIPTION = """
    'next-steps' - A list of two or more workflow steps to be processed in parallel. The next_steps MUST contain at least two values. If there is only one value, then the parallel step MUST NOT be used.
    Each entry in the next_steps property forms a branch of steps that are to be executed, even if there is only one workflow step in the branch. Each branch MUST reference a unique end step when that branch has completed processing. This allows implementations to know when to return to the original parallel step that started that branch to look for any on_completion, on_success, or on_failure actions.
    The definition of parallel execution and how many parallel steps that are possible to execute is implementation dependent and is not part of this specification.
    If any of the steps referenced in next_steps generate an error of any kind (exception or timeout) then implementers SHOULD consider defining rollback error handling for the playbook and include those steps in the playbook itself.
    Each ID MUST represent a CACAO workflow step object.
"""

WORKFLOW_STEP_TYPES_DESCRIPTION = f"""
    The type of workflow step being used.
    The value for this property MUST come from the workflow-step-type-enum enumeration.
    
    4.2 Workflow Step Type Enumeration
    Enumeration Name: workflow-step-type-enum
    This section defines the following types of workflow steps.
    
    'start' - 4.3 Start Step
    The start step workflow step is the starting point of a playbook and represents an explicit entry in the workflow to signify the start of a playbook. While this type inherits all of the common properties of a workflow step it does not define any additional properties. This workflow step MUST NOT use the on_success or on_failure properties.
    
    'end' - 4.4 End Step
    The end step workflow step is the ending point of a playbook or branch of step (e.g., a list of steps that are part of a parallel processing branch) and represents an explicit point in the workflow to signify the end of a playbook or branch of steps. While this type inherits all of the common properties of a workflow step it does not define any additional properties. When a playbook or branch of a playbook terminates it MUST call an end step. This workflow step MUST NOT use the on_completion, on_success, or on_failure properties. While an end step MUST exist for the overall workflow, additional end steps MAY be present for workflow branches.

    'action' - 4.5 Action Step
    The action step workflow step contains the actual commands to be executed by an agent against a set of targets. These commands are intended to be processed sequentially. In addition to the inherited properties, this section defines the following additional properties that are valid for this type.
    
    'playbook-action' - 4.6 Playbook Action Step
    The playbook action step workflow step executes a referenced playbook using the agents and targets defined in the referenced playbook. In addition to the inherited properties, this section defines the following additional properties that are valid for this type.

    'parallel' - {WORKFLOW_STEP_PARALLEL_DESCRIPTION}

    'if-condition' - 4.8 If Condition Step
    The if condition step workflow step defines the 'if-then-else' conditional logic that can be used within the workflow of the playbook. In addition to the inherited properties, this section defines the following additional properties that are valid for this type.

    'while-condition' - 4.9 While Condition Step
    The while condition step workflow step defines the 'while' conditional logic that can be used within the workflow of the playbook. In addition to the inherited properties, this section defines the following additional properties that are valid for this type.

    'switch-condition' - 4.10 Switch Condition Step
    The switch condition step workflow step defines the 'switch' condition logic that can be used within the workflow of the playbook. In addition to the inherited properties, this section defines the following additional properties that are valid for this type.
"""

WORKFLOW_STEP_ON_COMPLETION_DESCRIPTION = """
    'on_completion' - The ID of the next step to be processed upon completion of the defined commands.
    The value of this property MUST represent a CACAO workflow step object.
    If this property is defined, then on_success and on_failure MUST NOT be defined.
"""

WORKFLOW_STEP_ON_SUCCESS_DESCRIPTION = """
    'on_success' - The ID of the next step to be processed if this step completes successfully.
    The value of this property MUST represent a CACAO workflow step object.
    If this property is defined, then on_completion MUST NOT be defined. This property MUST NOT be used on the start or end steps.
"""

WORKFLOW_STEP_ON_FAILURE_DESCRIPTION = """
   'on_failure' - The ID of the next step to be processed if this step fails to complete successfully.
   The value of this property MUST represent a CACAO workflow step object.
   If omitted and a failure occurs, then the playbook’s exception handler found in the workflow_exception property at the Playbook level will be invoked.
   If this property is defined, then on_completion MUST NOT be defined. This property MUST NOT be used on the start or end steps.
"""

WORKFLOW_STEP_IF_CONDITION_DESCRIPTION = """
    'condition' - A boolean expression as defined in the STIX Patterning Grammar that when it evaluates as true executes the workflow step identified by the on_true property, otherwise it executes the on_false workflow step.
"""

WORKFLOW_STEP_IF_ON_TRUE_DESCRIPTION = """
    'on_true' - The step ID to be processed if the condition evaluates as true.
    The entry in the on_true property forms a branch of steps that are to be executed, even if there is only one workflow step in the branch. This branch MUST reference a unique end step when that branch has completed processing. This allows implementations to know when to return to the original if condition step that started that branch to look for any on_completion, on_success, or on_failure actions. 
    The ID MUST represent a CACAO workflow step object.
"""

WORKFLOW_STEP_IF_ON_FALSE_DESCRIPTION = """
    'on_false' - The step ID to be processed if the condition evaluates as false.
    The entry in the on_false property forms a branch of steps that are to be executed, even if there is only one workflow step in the branch. This branch MUST reference a unique end step when that branch has completed processing. This allows implementations to know when to return to the original if condition step that started that branch to look for any on_completion, on_success, or on_failure actions.
    The ID MUST represent a CACAO workflow step object.
"""


PLAYBOOK_VARIABLES = """
    Variables can be defined and then used as the playbook is executed. Variables are stored in a dictionary where the key is the name of the variable and the value is a variable data type. Variables can represent stateful elements that may need to be captured to allow for the successful execution of the playbook. All playbook variables are mutable unless identified as a constant.
    In addition to the rules for all dictionary keys, variable names:
        ● MUST be unique within the contextual scope they are declared
        ● Are case-sensitive (age, Age and AGE are three different variables) but SHOULD be lowercase
    The scope of a variable is determined by where the variable is declared. A variable may be defined globally for the entire playbook or locally within a workflow step. Variables are scoped to the object they are defined in, and any object that is used or referenced by that object. A specific variable can only be defined once, however, a variable can be assigned and used in the object where it is defined or in any object used or referenced by that object (e.g., a playbook variable can be assigned at the playbook level but also reassigned a different value within a workflow step).
"""
PLAYBOOK_VARIABLES_TYPES_VALID = [
    "bool",
    "dictionary",
    "float",
    "hexstring",
    "integer",
    "ipv4-addr",
    "ipv6-addr",
    "long",
    "mac-addr",
    "hash",
    "md5-hash",
    "sha256-hash",
    "string",
    "uri",
    "uuid",
]
PLAYBOOK_VARIABLES_DESCRIPTION = """
    Data Type: string
    A detailed description of this variable.
"""

PLAYBOOK_VARIABLES_TYPES = """
    The type of variable being used. The value for this property SHOULD come from the variable-type-ov vocabulary.
    Variable Type Vocabulary
    Vocabulary Name: variable-type-ov  
    
    'bool' - The value is a true or false value encoded as a string.
    Examples: "type": "bool", "value": "true"

    'dictionary' - The value contains a dictionary of values.   
    Examples: "type": "dictionary", "value": {"a":"fun"}

    'float' - A floating point number encoded as a string
    Examples: "type": "float", "value": "3.14159265"

    'hexstring' - Some string encoded in hexadecimal with a leading 0x.
    Examples: "type": "hexstring", "value": "0xFCA1"

    'integer' - An integer encoded as a string
    Examples: "type": "integer", "value": "123"

    'ipv4-addr' - An IPv4 network address (e.g., 127.0.0.1)
    Examples: "type": "ipv4-addr", "value": "127.0.0.1"

    'ipv6-addr' - An IPv6 network address (e.g, fe80::8785:b894:75aa:c16f) See [RFC 5952] for information about normalizing the address
    Examples: "type": "ipv6-addr", "value": "2001:db8::1"

    'long' - A long number value encoded as a string
    Examples: "type": "long", "value": "-2147483647"

    'mac-addr' - A layer 2 network MAC address (e.g., bc:d0:74:7a:3a:31)
    Examples: "type": "mac-addr", "value": "bc:d0:74:7a:3a:31"

    'hash' - A hash encoded as a string
    Examples: "type": "hash", "value": "ef9e7175fe883e3dc0d77dfad982846b"

    'md5-hash' - An MD5 hash encoded as a string
    Examples: "type": "md5-hash", "value": "ef9e7175fe883e3dc0d77dfad982846b"
    
    'sha256-hash' - A SHA 256 hash encoded as a string
    Examples: "type": "sha256-hash", "value": "c85406dd4c0b149a519a7715d5b8b17afe855594ef16eaada9be23a5aada155c"
    
    'string' - A normal string value
    Examples: "type": "string", "value": "some text"
    
    'uri' - A URI address
    Examples: "type": "uri", "value": "https://www.example.com/"
    
    'uuid' - An RFC 4122-compliant UUID [RFC4122].
    Examples: "type": "uuid", "value": "ded7157d-ba68-48c5-a093-b6c7b6bafd5f"  
"""

PLAYBOOK_VARIABLES_VALUES = """
    Data Type: string
    The value MUST be defined as one of the following JSON types: a string value, a number or boolean encoded as a JSON string, an empty string "", the special JSON NULL value, or a JSON object. NOTE: An empty string is NOT equivalent to a JSON NULL value. An empty string means the value is known to be empty. A value of NULL means the value is unknown or undefined.
"""

PLAYBOOK_VARIABLES_EXTERNAL = """
    Data Type: boolean
    This property only applies to playbook scoped variables.
    When set to true the variable declarationM defines that the variable’s initial value is passed into the playbook from a calling context.
    When set to false or omitted, the variable is defined within the playbook.
"""

PLAYBOOK_VARIABLES_CONSTANT = """
    Data Type: boolean
    This property defines if this variable is immutable. If true, the variable is immutable and MUST NOT be changed. If false, the variable is mutable and can be updated later on in the playbook. The default value is false. If this property is not present then the value is false.
"""
