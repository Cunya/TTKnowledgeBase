import { access, rename } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pagesRoot = path.join(appRoot, 'src', 'pages');
const localOnlyPages = ['pipeline.astro', 'progress.astro', 'recent.astro'];
const movedPages = [];
const productionBuild = process.env.GITHUB_ACTIONS === 'true' || process.env.PUBLIC_PRODUCTION_BUILD === 'true';

async function moveLocalPagesOutOfProduction() {
  for (const filename of localOnlyPages) {
    const source = path.join(pagesRoot, filename);
    const temporary = `${source}.local-only`;
    try {
      await access(source);
      await rename(source, temporary);
      movedPages.push({ source, temporary });
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
}

async function restoreLocalPages() {
  for (const { source, temporary } of movedPages.reverse()) {
    await rename(temporary, source);
  }
}

function runAstroBuild() {
  return new Promise((resolve, reject) => {
    const command = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    let child;
    try {
      child = spawn(command, ['run', 'build:astro'], {
        cwd: appRoot,
        stdio: 'inherit',
        shell: process.platform === 'win32',
      });
    } catch (error) {
      reject(error);
      return;
    }
    child.on('error', reject);
    child.on('close', (code, signal) => {
      if (signal) reject(new Error(`Astro build terminated by ${signal}`));
      else resolve(code ?? 1);
    });
  });
}

let exitCode = 1;
try {
  if (productionBuild) {
    await moveLocalPagesOutOfProduction();
  } else {
    process.env.PUBLIC_LOCAL_DOCS = 'true';
  }
  exitCode = await runAstroBuild();
} finally {
  await restoreLocalPages();
}
process.exitCode = exitCode;
