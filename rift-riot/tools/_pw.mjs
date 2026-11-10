// Finds Playwright whether it is a project dependency or a global install.
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';

export async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    const root = execSync('npm root -g').toString().trim();
    const require = createRequire(root + '/');
    return require('playwright');
  }
}
export const GL_ARGS = ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'];
