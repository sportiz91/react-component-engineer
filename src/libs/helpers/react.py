import json
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from src.libs.utils.types import LanguageOption, StylingOption
from src.libs.utils.file_system import delete_directory_recursive
from src.libs.utils.processes import run_yarn_install, find_available_port
from src.libs.utils.constants import (
    INDEX_HTML_CONTENT,
    GITIGNORE_CONTENT,
    ENV_CONTENT,
    ENV_EXAMPLE_CONTENT,
    README_CONTENT,
    ESLINTIGNORE_CONTENT,
    ESLINTRC_CONTENT,
    PRETTIERIGNORE_CONTENT,
    PRETTIERRC_CONTENT,
    TSCONFIG_CONTENT,
    CSS_MODULE_DECLARATION_CONTENT,
    TAILWIND_CONFIG_CONTENT,
    CRACO_CONFIG_CONTENT,
    POSTCSS_CONFIG_CONTENT,
    INDEX_CSS_CONTENT,
)


def get_index_content(language: LanguageOption, styling: StylingOption) -> str:
    content: str = (
        f"""
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
    )
    return content


def get_app_content(language: LanguageOption, styling: StylingOption) -> str:
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


def get_component_content(language: LanguageOption, styling: StylingOption) -> str:
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


def get_styling_import(styling: StylingOption, component_name: Optional[str] = None) -> str:
    if styling == "CSS Modules":
        return f"import styles from './{component_name or 'App'}.module.css';".strip() if component_name else "".strip()
    elif styling == "Tailwind":
        return "".strip()
    elif styling == "Material UI":
        return "import { ThemeProvider, createTheme } from '@mui/material/styles';".strip()


def get_theme_content(language: LanguageOption) -> str:
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


def get_styling_class(styling: StylingOption) -> str:
    if styling == "CSS Modules":
        return " className={styles.myComponent}".strip()
    elif styling == "Tailwind":
        return ' className="p-4 bg-gray-100 text-blue-500"'.strip()
    return ""


def get_package_json_content(language: LanguageOption, styling: StylingOption) -> str:
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


def run_eslint_prettier(base_path: str) -> Tuple[bool, str]:
    original_dir: str = os.getcwd()
    try:
        os.chdir(base_path)

        print("Running ESLint...")
        eslint_result: subprocess.CompletedProcess[str] = subprocess.run(["yarn", "run", "lint", "--fix"], capture_output=True, text=True)
        if eslint_result.returncode != 0:
            return False, f"ESLint encountered issues:\n{eslint_result.stderr}"

        print("Running Prettier...")
        prettier_result: subprocess.CompletedProcess[str] = subprocess.run(["yarn", "run", "format"], capture_output=True, text=True)
        if prettier_result.returncode != 0:
            return False, f"Prettier encountered issues:\n{prettier_result.stderr}"

        return True, "ESLint and Prettier ran successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Error running ESLint and Prettier: {str(e)}"
    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        os.chdir(original_dir)


def run_typescript_check(base_path: str) -> bool:
    original_dir: str = os.getcwd()
    try:
        os.chdir(base_path)
        result: subprocess.CompletedProcess[str] = subprocess.run(["yarn", "run", "tsc"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"TypeScript check failed:\n{result.stdout}\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Error running TypeScript check: {str(e)}")
        return False
    finally:
        os.chdir(original_dir)


async def run_typescript_checks(base_path: str) -> None:
    print("Running initial TypeScript check...")

    initial_check: bool = run_typescript_check(base_path)

    if initial_check:
        print("Initial TypeScript check passed.")
    else:
        print("Initial TypeScript check failed. This may be due to initialization. We'll check again shortly.")

    print("Waiting for TypeScript server to fully initialize...")

    await asyncio.sleep(5)

    print("Running final TypeScript check...")

    final_check: bool = run_typescript_check(base_path)

    if final_check:
        print("Final TypeScript check passed.")
    else:
        print("TypeScript errors persisted after the final check.")
        print("Try closing and reopening your editor, or run 'yarn tsc' in the project directory for more details.")


def create_react_app_structure(language: LanguageOption, styling: StylingOption, launch_browser: bool, base_path: Path) -> Tuple[Path, bool, str]:
    folders: List[str] = [
        "src",
        "public",
        "src/components",
    ]

    if delete_directory_recursive(base_path):
        print(f"Existing UI folder at {base_path} has been deleted.")

    base_path.mkdir(parents=True, exist_ok=True)

    for folder in folders:
        os.makedirs(base_path / folder, exist_ok=True)

    language_extension: str = "js" if language == "JavaScript" else "tsx"

    main_files: Dict[str, str] = {
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
        theme_extension: str = "ts" if language == "TypeScript" else "js"
        main_files[f"src/theme.{theme_extension}"] = get_theme_content(language)

    for file_path, content in main_files.items():
        try:
            file_full_path: Path = base_path / file_path
            os.makedirs(file_full_path.parent, exist_ok=True)
            with open(file_full_path, "w") as f:
                f.write(content)
        except IOError as e:
            print(f"Error writing file {file_path}: {str(e)}")

    if styling == "CSS Modules":
        with open(base_path / "src/components/MyComponent.module.css", "w") as f:
            f.write(".myComponent {\n  /* Add your styles here */\n}")

    success: bool
    message: str

    success, message = run_yarn_install(str(base_path))
    if not success:
        print(f"Warning: {message}")
        return base_path, False, message

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


def start_react_app(base_path: str) -> Tuple[bool, str]:
    original_dir: str = os.getcwd()
    try:
        os.chdir(base_path)

        print("Starting the React app. This may take a moment...")

        port: Optional[int] = find_available_port()
        if port is None:
            return False, "No available ports found between 3000 and 3010."

        env: Dict[str, str] = os.environ.copy()
        env["PORT"] = str(port)

        process: subprocess.Popen[str] = subprocess.Popen(["yarn", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

        assert process.stdout is not None, "stdout should not be None"
        for line in process.stdout:
            print(line, end="", flush=True)
            if "Compiled successfully" in line or "You can now view" in line:
                return True, f"React app started successfully. You can view it at http://localhost:{port}"

        assert process.stderr is not None, "stderr should not be None"
        error_output = process.stderr.read()
        return False, f"Failed to start React app. Error: {error_output}"
    except Exception as e:
        return False, f"An error occurred while starting the React app: {str(e)}"
    finally:
        os.chdir(original_dir)
