import os
from pathlib import Path
import json
import subprocess
import shutil
import asyncio
import socket


from src.apps.console.classes.commands.base import BaseCommand
from src.libs.helpers.console import get_user_input


INDEX_HTML_CONTENT = """
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
""".strip()


GITIGNORE_CONTENT = """\
# Dependencies
/node_modules

# Production
/build

# Misc
.DS_Store
.env.local
.env.development.local
.env.test.local
.env.production.local

npm-debug.log*
yarn-debug.log*
yarn-error.log*
""".strip()

ENV_CONTENT = """\
REACT_APP_API_URL=http://localhost:3000
REACT_APP_ENV=development
""".strip()

ENV_EXAMPLE_CONTENT = """\
REACT_APP_API_URL=http://example.com/api
REACT_APP_ENV=production
""".strip()

README_CONTENT = """\
# React App

This project was bootstrapped with a custom React app generator.

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### `npm test`

Launches the test runner in the interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.
""".strip()

ESLINTIGNORE_CONTENT = """\
node_modules
build
**/*.html
""".strip()

ESLINTRC_CONTENT = """\
{
  "extends": [
    "react-app",
    "react-app/jest"
  ],
  "rules": {
    "no-console": "warn"
  },
  "env": {
    "browser": true,
    "node": true,
    "es6": true
  },
  "parserOptions": {
    "ecmaVersion": 2020,
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    }
  }
}
""".strip()

PRETTIERIGNORE_CONTENT = """\
node_modules
build
coverage
""".strip()

PRETTIERRC_CONTENT = """\
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
""".strip()

TAILWIND_CONFIG_CONTENT = """
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
""".strip()

POSTCSS_CONFIG_CONTENT = """
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""".strip()

CRACO_CONFIG_CONTENT = """
const path = require('path');

module.exports = {
  style: {
    postcss: {
      loaderOptions: (postcssLoaderOptions) => {
        postcssLoaderOptions.postcssOptions = {
          config: path.resolve(__dirname, 'postcss.config.js'),
        };
        return postcssLoaderOptions;
      },
    },
  },
};
""".strip()


INDEX_CSS_CONTENT = """
@tailwind base;
@tailwind components;
@tailwind utilities;
""".strip()

TSCONFIG_CONTENT = """\
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "typeRoots": ["./node_modules/@types"]
  },
  "include": ["src"]
}
""".strip()

CSS_MODULE_DECLARATION_CONTENT = """\
/// <reference types="react-scripts" />

declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}
""".strip()


def get_index_content(language, styling):
    content = f"""
import React from 'react';
import ReactDOM from 'react-dom/client';
{"import './index.css';" if styling == "Tailwind" else ""}
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'){" as HTMLElement" if language == "TypeScript" else ""});
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""".strip()
    return content


def get_app_content(language, styling):
    if styling == "Material UI":
        if language == "TypeScript":
            return """
import React from 'react';
import { ThemeProvider } from '@mui/material/styles';

import MyComponent from './components/MyComponent';
import theme from './theme';

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <MyComponent />
    </ThemeProvider>
  );
};

export default App;
""".strip()
        else:
            return """
import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import MyComponent from './components/MyComponent';

import theme from './theme';

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <MyComponent />
    </ThemeProvider>
  );
};

export default App;
""".strip()
    else:
        return f"""
import React from 'react';
import MyComponent from './components/MyComponent';
{get_styling_import(styling)}

const App{' = () =>' if language == 'JavaScript' else ': React.FC = () =>'} {{
  return (
    <div className="App">
      <MyComponent />
    </div>
  );
}};

export default App;
""".strip()


def get_component_content(language, styling):
    if styling == "Material UI":
        if language == "TypeScript":
            return """
import React from 'react';
import { Card, Typography } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { Theme } from '@mui/material/styles';

const useStyles = makeStyles((theme: Theme) => ({
  card: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.secondary.main,
    padding: theme.spacing(2),
    margin: '0 auto',
    maxWidth: '500px',
  },
}));

const MyComponent: React.FC = () => {
  const classes = useStyles();

  return (
    <Card className={classes.card}>
      <Typography variant="h5">Hello React Coder!</Typography>
    </Card>
  );
};

export default MyComponent;
""".strip()
        else:
            return """
import React from 'react';
import { Card, Typography } from '@mui/material';
import { makeStyles } from '@mui/styles';

const useStyles = makeStyles((theme) => ({
  card: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.secondary.main,
    padding: theme.spacing(2),
    margin: '0 auto',
    maxWidth: '500px',
  },
}));

const MyComponent = () => {
  const classes = useStyles();

  return (
    <Card className={classes.card}>
      <Typography variant="h5">Hello React Coder!</Typography>
    </Card>
  );
};

export default MyComponent;
""".strip()
    elif styling == "Tailwind":
        return f"""
import React from 'react';
import '../index.css';

const MyComponent{' = () =>' if language == 'JavaScript' else ': React.FC = () =>'} {{
  return (
    <div className="p-4 bg-gray-100 text-blue-500">
      Hello React Coder!
    </div>
  );
}};

export default MyComponent;
""".strip()
    else:
        return f"""
import React from 'react';
{get_styling_import(styling, 'MyComponent')}

const MyComponent{' = () =>' if language == 'JavaScript' else ': React.FC = () =>'} {{
  return (
    <div {get_styling_class(styling)}>
      Hello React Coder!
    </div>
  );
}};

export default MyComponent;
""".strip()


def get_styling_import(styling, component_name=None):
    if styling == "CSS Modules":
        return f"import styles from './{component_name or 'App'}.module.css';".strip() if component_name else "".strip()
    elif styling == "Tailwind":
        return "".strip()
    elif styling == "Material UI":
        return "import { ThemeProvider, createTheme } from '@mui/material/styles';".strip()
    return "".strip()


def get_theme_content(language):
    if language == "TypeScript":
        return """
import { createTheme, Theme as MuiTheme } from '@mui/material/styles';

declare module "@mui/styles/defaultTheme" {
  interface DefaultTheme extends MuiTheme {}
}

const theme: MuiTheme = createTheme({
    palette: {
        primary: {
            main: '#1976d2',
        },
        secondary: {
            main: '#dc004e',
        },
    },
});

export default theme;
""".strip()
    else:
        return """
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        primary: {
            main: '#1976d2',
        },
        secondary: {
            main: '#dc004e',
        },
    },
});

export default theme;
""".strip()


def get_styling_class(styling):
    if styling == "CSS Modules":
        return " className={styles.myComponent}".strip()
    elif styling == "Tailwind":
        return ' className="p-4 bg-gray-100 text-blue-500"'.strip()
    return ""


def get_package_json_content(language, styling):
    dependencies = {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "react-scripts": "5.0.1",
    }
    dev_dependencies = {
        "eslint": "^8.40.0",
        "prettier": "^2.8.8",
    }
    scripts = {
        "start": "react-scripts start",
        "build": "react-scripts build",
        "test": "react-scripts test",
        "eject": "react-scripts eject",
        "lint": "eslint .",
        "format": "prettier --write .",
    }
    browsers = {"production": [">0.2%", "not dead", "not op_mini all"], "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]}

    if language == "TypeScript":
        dependencies.update(
            {
                "@types/react": "^18.0.28",
                "@types/react-dom": "^18.0.11",
                "@types/node": "^14.14.31",
                "typescript": "^4.9.5",
            }
        )
        scripts.update({"tsc": "tsc --noEmit"})

    if styling == "Material UI":
        dependencies.update(
            {
                "@mui/material": "^5.11.10",
                "@mui/styles": "^5.11.10",
                "@mui/system": "^5.11.10",
                "@emotion/react": "^11.10.6",
                "@emotion/styled": "^11.10.6",
            }
        )
        if language == "TypeScript":
            dependencies["@mui/types"] = "^7.2.3"

    if styling == "Tailwind":
        scripts.update(
            {
                "start": "craco start",
                "build": "craco build",
                "test": "craco test",
            }
        )
        dependencies.update(
            {
                "tailwindcss": "^3.2.7",
                "postcss": "^8.4.21",
                "autoprefixer": "^10.4.13",
            }
        )
        dev_dependencies.update(
            {
                "@craco/craco": "^7.0.0-alpha.9",
                "@craco/types": "^7.0.0-alpha.9",
            }
        )

    if language == "TypeScript":
        scripts["start"] = "react-scripts --openssl-legacy-provider start"
        scripts["build"] = "react-scripts --openssl-legacy-provider build"

    return json.dumps(
        {
            "name": "react-app",
            "version": "0.1.0",
            "private": True,
            "dependencies": dependencies,
            "devDependencies": dev_dependencies,
            "scripts": scripts,
            "browserslist": browsers,
        },
        indent=2,
    ).strip()


def run_eslint_prettier(base_path):
    original_dir = os.getcwd()
    try:
        os.chdir(base_path)

        if shutil.which("yarn") is None:
            return False, "Yarn is not installed. Please install Yarn and try again."

        print("Running yarn install...")
        install_result = subprocess.run(["yarn", "install", "--force"], capture_output=True, text=True)
        if install_result.returncode != 0:
            return False, f"Error during yarn install:\n{install_result.stderr}"

        print("Running ESLint...")
        eslint_result = subprocess.run(["yarn", "run", "lint", "--fix"], capture_output=True, text=True)
        if eslint_result.returncode != 0:
            return False, f"ESLint encountered issues:\n{eslint_result.stderr}"

        print("Running Prettier...")
        prettier_result = subprocess.run(["yarn", "run", "format"], capture_output=True, text=True)
        if prettier_result.returncode != 0:
            return False, f"Prettier encountered issues:\n{prettier_result.stderr}"

        return True, "ESLint and Prettier ran successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Error running ESLint and Prettier: {str(e)}"
    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        os.chdir(original_dir)


def run_typescript_check(base_path):
    original_dir = os.getcwd()
    try:
        os.chdir(base_path)
        result = subprocess.run(["yarn", "run", "tsc"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"TypeScript check failed:\n{result.stdout}\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Error running TypeScript check: {str(e)}")
        return False
    finally:
        os.chdir(original_dir)


async def run_typescript_checks(base_path):
    print("Running initial TypeScript check...")

    initial_check = run_typescript_check(base_path)

    if initial_check:
        print("Initial TypeScript check passed.")
    else:
        print("Initial TypeScript check failed. This may be due to initialization. We'll check again shortly.")

    print("Waiting for TypeScript server to fully initialize...")

    await asyncio.sleep(5)

    print("Running final TypeScript check...")

    final_check = run_typescript_check(base_path)

    if final_check:
        print("Final TypeScript check passed.")
    else:
        print("TypeScript errors persisted after the final check.")
        print("Try closing and reopening your editor, or run 'yarn tsc' in the project directory for more details.")


def find_available_port(start_port=3000, max_port=3010):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except socket.error:
                continue
    return None


def create_react_app_structure(language, styling, launch_browser):
    base_path = Path(__file__).resolve().parents[4] / "apps" / "ui"

    folders = [
        "src",
        "public",
        "src/components",
    ]

    if delete_directory_recursive(base_path):
        print(f"Existing UI folder at {base_path} has been deleted.")

    base_path.mkdir(parents=True, exist_ok=True)

    for folder in folders:
        os.makedirs(base_path / folder, exist_ok=True)

    language_extension = "js" if language == "JavaScript" else "tsx"

    main_files = {
        "public/index.html": INDEX_HTML_CONTENT,
        f"src/index.{language_extension}": get_index_content(language, styling),
        f"src/App.{language_extension}": get_app_content(language, styling),
        f"src/components/MyComponent.{language_extension}": get_component_content(language, styling),
        "package.json": get_package_json_content(language, styling),
        ".gitignore": GITIGNORE_CONTENT,
        ".env": ENV_CONTENT,
        ".env.example": ENV_EXAMPLE_CONTENT,
        "README.md": README_CONTENT,
        ".eslintignore": ESLINTIGNORE_CONTENT,
        ".eslintrc": ESLINTRC_CONTENT,
        ".prettierignore": PRETTIERIGNORE_CONTENT,
        ".prettierrc": PRETTIERRC_CONTENT,
    }

    if language == "TypeScript":
        main_files["tsconfig.json"] = TSCONFIG_CONTENT
        main_files["src/react-app-env.d.ts"] = CSS_MODULE_DECLARATION_CONTENT
        main_files["src/index.tsx"] = get_index_content(language, styling)

    if styling == "Tailwind":
        main_files.update(
            {
                "tailwind.config.js": TAILWIND_CONFIG_CONTENT,
                "craco.config.js": CRACO_CONFIG_CONTENT,
                "postcss.config.js": POSTCSS_CONFIG_CONTENT,
                "src/index.css": INDEX_CSS_CONTENT,
            }
        )

    if styling == "Material UI":
        theme_extension = "ts" if language == "TypeScript" else "js"
        main_files[f"src/theme.{theme_extension}"] = get_theme_content(language)

    for file_path, content in main_files.items():
        try:
            file_full_path = base_path / file_path
            os.makedirs(file_full_path.parent, exist_ok=True)
            with open(file_full_path, "w") as f:
                f.write(content)
        except IOError as e:
            print(f"Error writing file {file_path}: {str(e)}")

    if styling == "CSS Modules":
        with open(base_path / "src/components/MyComponent.module.css", "w") as f:
            f.write(".myComponent {\n  /* Add your styles here */\n}")

    success, message = run_eslint_prettier(base_path)

    if not success:
        print(f"Warning: {message}")
    else:
        print(message)

    if language == "TypeScript":
        if not run_typescript_check(base_path):
            print("Warning: TypeScript check failed. Please review your code for type errors.")

    if launch_browser:
        success, message = start_react_app(base_path)
        print(message)
    else:
        success = True
        print("React app structure created successfully. You can start it manually later.")

    return base_path, success, message


def start_react_app(base_path):
    original_dir = os.getcwd()
    try:
        os.chdir(base_path)

        print("Starting the React app. This may take a moment...")

        port = find_available_port()
        if port is None:
            return False, "No available ports found between 3000 and 3010."

        env = os.environ.copy()
        env["PORT"] = str(port)

        process = subprocess.Popen(["yarn", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

        for line in process.stdout:
            print(line, end="", flush=True)
            if "Compiled successfully" in line or "You can now view" in line:
                return True, f"React app started successfully. You can view it at http://localhost:{port}"

        error_output = process.stderr.read()
        return False, f"Failed to start React app. Error: {error_output}"
    except Exception as e:
        return False, f"An error occurred while starting the React app: {str(e)}"
    finally:
        os.chdir(original_dir)


def delete_directory_recursive(directory_path):
    try:
        path = Path(directory_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False
    except Exception as e:
        print(f"An error occurred while trying to delete the directory: {e}")
        return False


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

        launch_browser = await get_user_input("Do you want to start the app and open it in the browser after creation?", choices=["Yes", "No"], default="Yes")
        launch_browser = launch_browser.lower() == "yes"

        self.console.print("Creating React app structure...", style="bold green")

        base_path, success, message = create_react_app_structure(language, styling, launch_browser)

        self.console.print(f"React app structure created successfully at {base_path}", style="bold green")
        self.console.print("ESLint and Prettier have been run on the generated files.", style="bold green")

        if language == "TypeScript":
            await run_typescript_checks(base_path)
            self.console.print("TypeScript compilation check has been run.", style="bold green")
            self.console.print(
                "If you encounter any TypeScript errors, please try closing your editor and opening it again or running 'yarn tsc' in the project directory for more details.",
                style="bold yellow",
            )

        if launch_browser:
            if success:
                self.console.print(message, style="bold green")
                self.console.print("To stop the app, press Ctrl+C in this console.", style="bold green")
            else:
                self.console.print("The React app structure was created, but there was an issue starting the app.", style="bold yellow")
                self.console.print(message, style="bold yellow")
                self.console.print("You can try starting it manually by navigating to the app directory and running 'yarn start'.", style="bold yellow")
        else:
            self.console.print("To start the app later, navigate to the app directory and run 'yarn start'.", style="bold green")

        self.console.print("Command execution completed.", style="bold green")
