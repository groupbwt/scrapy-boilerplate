const path = require('path');
const fs = require('fs');

const PROJECT_PREFIX = 'PROJECT_PREFIX';
const MAX_MEMORY_RESTART = '1024M';

const _projectDirectory = path.join(process.cwd(), '..');
const PM2_LOG_DIRECTORY = path.join(_projectDirectory, 'logs');

const [pythonEnabled, typescriptEnabled] = [true, true];
const PYTHON_CWD = path.join(_projectDirectory, 'src', 'python', 'src');
const TYPESCRIPT_CWD = path.join(_projectDirectory, 'src', 'typescript', 'src');
if (pythonEnabled && !fs.lstatSync(PYTHON_CWD).isDirectory()) {
  console.error('no working directory for python was found');
  process.exit(1);
}
if (typescriptEnabled && !fs.lstatSync(TYPESCRIPT_CWD).isDirectory()) {
  console.error('no working directory for typescript was found');
  process.exit(1);
}

let PYTHON_INTERPRETER = null;
let SCRAPY_SCRIPT = null;
let NODEJS_SCRIPT = 'node';
if (process.platform === 'win32') {
  PYTHON_INTERPRETER = path.join(PYTHON_CWD, '.venv', 'Scripts', 'python.exe');
  SCRAPY_SCRIPT = path.join(PYTHON_CWD, '.venv', 'Scripts', 'scrapy.exe');
} else {
  PYTHON_INTERPRETER = path.join(PYTHON_CWD, '.venv', 'bin', 'python');
  SCRAPY_SCRIPT = path.join(PYTHON_CWD, '.venv', 'bin', 'scrapy');
}

if (!fs.existsSync(PYTHON_INTERPRETER)) {
  console.error('ERROR: python(virtualenv) not found');
  process.exit(1);
}
if (!fs.existsSync(PYTHON_INTERPRETER)) {
  console.error('ERROR: scrapy not found');
  process.exit(1);
}

module.exports = {
  PYTHON_INTERPRETER,
  SCRAPY_SCRIPT,
  PROJECT_PREFIX,
  MAX_MEMORY_RESTART,
  PYTHON_CWD,
  TYPESCRIPT_CWD,
  PM2_LOG_DIRECTORY,
  NODEJS_SCRIPT,
};
