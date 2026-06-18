"""Workflow executor — the orchestration core.

Given a workflow (parsed from YAML), a device registry, and a set of parameters,
it runs the steps in order, threads each device's outputs into the next device's
'upstream', and returns one structured experiment record.
"""


def execute_workflow(workflow, devices, parameters):
    """Run one full experiment and return a record of what happened.

    Args:
        workflow: the parsed YAML dict (has a 'steps' list).
        devices: the name->device registry from build_cdte_devices().
        parameters: the parameter values to run this experiment at.
    """
    # This dict accumulates measurements as we go, and is passed to each device
    # as 'upstream' so later devices can use earlier results.
    upstream = {}

    # We'll record each step's result here, for traceability.
    step_records = []

    # Run each step in the order defined by the YAML.
    for step in workflow["steps"]:
        step_name = step["name"]
        device_name = step["device"]

        # Look up the actual device object by its name.
        device = devices[device_name]

        # Run the device, giving it the parameters AND everything measured so far.
        result = device.run({"parameters": parameters, "upstream": upstream})

        # Record what this step did.
        step_records.append({
            "step": step_name,
            "device": device_name,
            "status": result["status"],
            "outputs": result["outputs"],
        })

        # If this device failed, stop the whole experiment here (short-circuit).
        # A failed sample makes all downstream measurements meaningless.
        if result["status"] == "failed":
            return {
                "parameters": parameters,
                "status": "failed",
                "objective_score": None,           # no valid score on failure
                "failure_category": result["failure_category"],
                "measurements": upstream,
                "steps": step_records,
            }

        # Add this device's measurements into upstream for the next device.
        upstream.update(result["outputs"])

    # The final objective score is the pce_proxy produced by the last device.
    objective_score = upstream.get("pce_proxy")

    return {
        "parameters": parameters,
        "status": "completed",
        "objective_score": objective_score,
        "failure_category": None,
        "measurements": upstream,
        "steps": step_records,
    }