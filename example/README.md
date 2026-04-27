# lib_6107 Example Robot

This robot provides an example of how to use the [lib_6107](https://github.com/CyberJagzz/frclib-6107)
module library. This project also exists to assist in unit testing.

# Initial creation

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
module.

I will leave it to you to create a basic robot with the above instructions and then _diff_
it with this example to see the differences.