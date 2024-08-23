import os
from pathlib import Path

from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input


# @TODO: include package.json, .gitignore, README.md, .env, .env.example, .eslintignore, .eslintrc, .prettierignore, .prettierrc, .gitattributes, .editorconfig
# And more...
# I can add a .env here to my own repo to say dev vs prod mode, on dev I can add commands that are not going to be on prod, for example
# I can add a command that deletes automatically for me the UI folder.
def create_react_app_structure(language, styling):
    base_path = Path(__file__).resolve().parents[4] / "apps" / "ui"

    folders = ["src", "public", "src/components"]

    for folder in folders:
        os.makedirs(base_path / folder, exist_ok=True)

    language_extension = get_extension(language)

    main_files = {
        "public/index.html": get_index_html_content(),
        f"src/index.{language_extension}": get_index_content(language),
        f"src/App.{language_extension}": get_app_content(language, styling),
        f"src/components/MyComponent.{language_extension}": get_component_content(language, styling),
    }

    for file_path, content in main_files.items():
        with open(base_path / file_path, "w") as f:
            f.write(content)

    if styling == "CSS Modules":
        with open(base_path / "src/components/MyComponent.module.css", "w") as f:
            f.write(".myComponent {\n  /* Add your styles here */\n}")


def get_extension(language):
    return "js" if language == "JavaScript" else "tsx"


def get_index_html_content():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>React App</title>
    </head>
    <body>
        <noscript>You need to enable JavaScript to run this app.</noscript>
        <div id="root"></div>
    </body>
    </html>
"""


def get_index_content(language):
    if language == "JavaScript":
        return """
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
    else:
        return """
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""


def get_app_content(language, styling):
    if language == "JavaScript":
        return f"""
import React from 'react';
import MyComponent from './components/MyComponent';
{get_styling_import(styling)}

function App() {{
  return (
    <div className="App">
      <MyComponent />
    </div>
  );
}}

export default App;
"""
    else:
        return f"""
import React from 'react';
import MyComponent from './components/MyComponent';
{get_styling_import(styling)}

const App: React.FC = () => {{
  return (
    <div className="App">
      <MyComponent />
    </div>
  );
}}

export default App;
"""


def get_component_content(language, styling):
    if language == "JavaScript":
        return f"""
import React from 'react';
{get_styling_import(styling, 'MyComponent')}

function MyComponent() {{
  return (
    <div{get_styling_class(styling)}>
      Hello React Coder!
    </div>
  );
}}

export default MyComponent;
"""
    else:
        return f"""
import React from 'react';
{get_styling_import(styling, 'MyComponent')}

const MyComponent: React.FC = () => {{
  return (
    <div{get_styling_class(styling)}>
      Hello React Coder!
    </div>
  );
}}

export default MyComponent;
"""


def get_styling_import(styling, component_name=None):
    if styling == "CSS Modules":
        return f"import styles from './{component_name or 'App'}.module.css';" if component_name else ""
    elif styling == "Tailwind":
        return "import 'tailwindcss/tailwind.css';"
    elif styling == "Material UI":
        return "import { ThemeProvider, createTheme } from '@mui/material/styles';"
    return ""


def get_styling_class(styling):
    if styling == "CSS Modules":
        return " className={styles.myComponent}"
    elif styling == "Tailwind":
        return ' className="p-4 bg-gray-100 text-blue-500"'
    return ""


class CreateReactComponentCommand(BaseCommand):
    name = "create react component"
    description = "Create a new React component"

    async def execute(self, *args, **kwargs):
        description = await get_user_input("Please enter a description of the component: ")
        self.console.print(f"Component description: {description}", style="bold green")

        language = await get_user_input("Do you want to use JavaScript or TypeScript?", choices=["JavaScript", "TypeScript"], default="JavaScript")
        self.console.print(f"You chose: {language}", style="bold green")

        styling = await get_user_input("Which styling option do you prefer?", choices=["CSS Modules", "Tailwind", "Material UI"], default="CSS Modules")
        self.console.print(f"You chose: {styling}", style="bold green")

        self.console.print("Component creation logic will be implemented in the next step.", style="bold green")

        create_react_app_structure(language, styling)

        self.console.print("Component's structure created successfully", style="bold green")
