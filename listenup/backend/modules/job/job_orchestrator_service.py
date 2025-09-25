"""
in teh backend app we will construct the full_job_payload which takes
user inputs and merges them with the manifest defaults to create
the full job definition. This object will be saved as "the job" in the
nosql store and when an event is received to process a job, the 
microservice will fetch the full job payload from the job management endpoint and begin to process.

it is the responsibility of this backend service to ensure that the job payload is valid
and complete before saving it to the job store, so the microservices can run it safely.

example:
full_job_data = {
    "job_id": "job_12345",
    "state": "pending",
    "current_step_index": 0,
    "steps": [
        {
            
            "name": "ampslice",
            "step_type": "flucoma",
            "command_template": (
                "fluid-ampslice "
                "{source} {indices} "
                "-onthreshold {onthreshold} "
                "-offthreshold {offthreshold} "
                "-slowrampup {slowrampup} "
                "-slowrampdown {slowrampdown} "
                "-fastrampup {fastrampup} "
                "-fastrampdown {fastrampdown} "
                "-floor {floor} "
                "-highpassfreq {highpassfreq} "
                "-minslicelength {minslicelength} "
                "-numchans {numchans} "
                "-numframes {numframes} "
                "-startchan {startchan} "
                "-startframe {startframe} "
                "-warnings {warnings}"
            ),
            "inputs": {
                "source": "s3://bucket/audio/input.wav",
                "onthreshold": 0.5,
                "offthreshold": -20.0,
                "slowrampup": 100,
                "slowrampdown": 100,
                "fastrampup": 1,
                "fastrampdown": 1,
                "floor": -144.0,
                "highpassfreq": 85.0,
                "minslicelength": 2,
                "numchans": -1,
                "numframes": -1,
                "startchan": 0,
                "startframe": 0,
                "warnings": 1
            },
            "outputs": {
                "indices": "output_indices.json"
            }
        }
    ]
}
"""