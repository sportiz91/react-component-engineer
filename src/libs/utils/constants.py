INDEX_HTML_CONTENT: str = (
    """
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
)


GITIGNORE_CONTENT: str = (
    """\
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
)

ENV_CONTENT: str = (
    """\
REACT_APP_API_URL=http://localhost:3000
REACT_APP_ENV=development
""".strip()
)

ENV_EXAMPLE_CONTENT: str = (
    """\
REACT_APP_API_URL=http://example.com/api
REACT_APP_ENV=production
""".strip()
)

README_CONTENT: str = (
    """\
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
)

ESLINTIGNORE_CONTENT: str = (
    """\
node_modules
build
**/*.html
""".strip()
)

ESLINTRC_CONTENT: str = (
    """\
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
)

PRETTIERIGNORE_CONTENT: str = (
    """\
node_modules
build
coverage
""".strip()
)

PRETTIERRC_CONTENT: str = (
    """\
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
""".strip()
)

TAILWIND_CONFIG_CONTENT: str = (
    """
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
)

POSTCSS_CONFIG_CONTENT: str = (
    """
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""".strip()
)

CRACO_CONFIG_CONTENT: str = (
    """
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
)


INDEX_CSS_CONTENT: str = (
    """
@tailwind base;
@tailwind components;
@tailwind utilities;
""".strip()
)

TSCONFIG_CONTENT: str = (
    """\
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
)

CSS_MODULE_DECLARATION_CONTENT: str = (
    """\
/// <reference types="react-scripts" />

declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}
""".strip()
)

CODE_CHANGES: str = """
Only show me code changes with a clear indication of where they should be placed.

"""

ENTIRE_FILE: str = """
Please, output the modified files with the changes added to it, so I can copy paste it into my codebase.

If you cannot output the entire file with the modified changes due to your own limitations, please respond with:
<CONTEXT_WINDOW_EXCEEDED>

Ensure only <CONTEXT_WINDOW_EXCEEDED> is in the response and nothing else.

"""

CLAUDE_CONTEXT_WINDOW: int = 200000

DASHED_MARKERS_EXPLANATION: str = """
The markers --- Filename path/to/file.py --- and --- End of Filename path/to/file.py --- 
indicate the start and end of the full content of the specified file. 

For example:

<example>
  --- Filename src/main.py ---
  print('Hello, World!')
  --- End of Filename src/main.py ---
</example>
"""


XML_MARKERS_EXPLANATION: str = """
The <documents> tag contains multiple <document> tags, each representing a file (code).
Each <document> tag contains a <source> tag with the filename and a <document_content> tag with the content of the file.
On the <source> tag, the index attribute represents the order of the file in the list.

For example:

<documents>
  <document index="1">
    <source>src/main.py</source>
    <document_content>
      print('Hello, World!')
    </document_content>
  </document>
</documents>
"""

CHAIN_OF_THOUGHT: str = """
Let's think step-by-step on how to solve this problem. Output your thinking process between <thinking> tags, and the solution between <answer> tags.
"""
