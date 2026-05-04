# lib_6107 Example Robot

This robot provides an example of how to use the [lib_6107](https://github.com/CyberJagzz/frclib-6107)
module library. This project also exists to assist in unit testing.

## Initial creation

The following commands were used to create this project. They do not need to be ran
again for this example project, but it does outline how to create a project from scratch
and then modify it to make use of the frclib-6107 module.

```shell
cd example

uv venv     # Create virtual environment directory 
uv pip install robotpy

python -m robotpy init            # Create the skeleton files for a robot
python -m robotpy add-tests       # Add unit tests capability
python -m robotpy create-physics  # And finally add simulation support 
```
This will create the basic structures.  I then modified the pyproject.toml file to include
much of what we will be needing. As well as the imports for pulling in the frclib_6107
module.  The basic files created, and then modified by me, from the above commands are:

    - `pyproject.toml`
    - `robot.py`
    - `physics.py`
    - `tests/test_robot.py`

I will leave it to you to create a basic robot with the above instructions and then _diff_
it with this example to see the differences.

## Second Round of Modifications

For the second round of modifications, I added the following files to the project with references
in them as needed in the files from the initial creation step:

    - `constants.py`
    - `robotcontainer.py`
    - 'generated/tuner_constants.py, and
    - the initial subsystems and util sibdirectories

Many of files above were copied over from our [2026-Rebuilt](https://github.com/6107/2026-Rebuilt) repository
and cleaned up a bit to give us a nice starting point for this example robot. For this robot, we will
only be creating a two subsystems besides the drivetrain. Near the end of this example project, I
hope to also add Vision support.

## Drivetrain Subsystem


### Running under simulation


## Flywheel Subsystem

The flywheel makes use of a RPM based subsystem specialized class

## Climber Subsystem

The climber is a simple subsystem that makes use of the basic subsystem class. It is not RPM based, but
eventually the hope is that we can modify it to use a base 'elevator' subsystem class.

## Other Possible Subsystems

A common subsystem design is one that in an angle based subsystem. This is common for arms, and 
other similar mechanisms. We do not have one of these at this time. Hopefully we can add on
in the future and derive an 'Arm' subsystem class from it.


Another common subsystem design is one that is position based that is not an elevator but is also
'angle' based. This is common for a turret where the position is based on any angle and typically
can rotate > 360 degrees. We do not have one of these at this time either, but it is something
we hope to add.

## Vision Subsystem


# Automation


## PathPlanner

