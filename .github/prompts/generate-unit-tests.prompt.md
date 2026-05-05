# Instructions
You are an expert Python developer. Generate pytest unit tests for the 
provided code.

## Requirements
- **Framework**: Use `pytest` as the testing framework.
- **Naming**: Name tests starting with `test_` and ending with a suffix describing the behavior (e.g., `test_sum_handles_negative_numbers`).
- **Pattern**: Follow the **Arrange/Act/Assert** pattern.
- **Data-Driven**: Use `pytest.mark.parametrize` for data-driven tests where feasible.
- **Scenarios**: Include positive, negative, and edge case scenarios.
- **Exceptions**: Use `pytest.raises` for testing expected exceptions.
- **Shared Setup**: Use `pytest.fixture` for reusable setup logic.
- **Mocking**: Mock external dependencies using `unittest.mock` or pytest fixtures.
- **Coverage**: Ensure that the tests cover all critical paths and edge cases in the code, aiming for high code coverage.

## Output Format
Generate the unit tests in a Python file format, ensuring that the tests are 
well-structured and adhere to best practices for readability and maintainability. 
Include comments where necessary to explain the purpose of each test case.

## Output Filename and Location
Save the generated unit tests in a file named `test_<original_module_name>.py`, 
where `<original_module_name>` is the name of the module containing the code being tested. 
Place this file in the tests directory of the project structure and ensure it is 
organized in a subdirectory that mirrors the structure of the source code for 
clarity and maintainability.

