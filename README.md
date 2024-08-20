# React Component Engineer

Create automatically React Component that self-improves.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- You have installed the latest version of Python
- You have a Windows/Linux/Mac machine.

## Installation

To install the project, follow these steps:

1. Clone the repository:

   ```
   git clone [your-repo-link]
   cd [your-project-directory]
   ```

2. Create a virtual environment:

   ```
   python -m venv react-component-engineer
   ```

3. Activate the virtual environment:

   - On Windows:
     ```
     react-component-engineer\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source react-component-engineer/bin/activate
     ```

4. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

5. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Then, open the `.env` file and replace "YOUR API KEY" with your actual API keys for Anthropic, OpenAI, and Tavily.

## Usage

To use the project, follow these steps:

1. Ensure your virtual environment is activated.

## Development

This project uses the following development tools:

- flake8 for linting (configuration in `.flake8`)
- black for code formatting (configuration in `pyproject.toml`)
