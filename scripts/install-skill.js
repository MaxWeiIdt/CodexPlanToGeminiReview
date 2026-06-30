const fs = require('fs');
const path = require('path');
const os = require('os');

const homeDir = os.homedir();
const repoRoot = path.resolve(__dirname, '..');

const sourceSkillDir = path.join(repoRoot, 'environment-files', 'user-home', 'agents', 'skills', 'gemini-review');
const sourceCodexDir = path.join(repoRoot, 'environment-files', 'user-home', 'codex');
const sourceReviewScript = path.join(sourceCodexDir, 'review-scripts', 'gemini_review.py');
const sourceStopHook = path.join(sourceCodexDir, 'hooks', 'stop_review_gate.py');
const sourceHooksExample = path.join(sourceCodexDir, 'hooks.example.json');
const sourceSecretsExample = path.join(sourceCodexDir, 'gemini-review.secrets.example.json');
const sourceAgents = path.join(sourceCodexDir, 'AGENTS.md');

const targetCodexSkillDir = path.join(homeDir, '.agents', 'skills', 'gemini-review');
const targetCodexDir = path.join(homeDir, '.codex');
const targetCodexHooksDir = path.join(targetCodexDir, 'hooks');
const targetCodexReviewScriptsDir = path.join(targetCodexDir, 'review-scripts');

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function assertExists(sourcePath) {
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`找不到來源檔案或資料夾: ${sourcePath}`);
  }
}

function copyFolderSync(from, to) {
  assertExists(from);
  ensureDir(to);

  for (const element of fs.readdirSync(from)) {
    const source = path.join(from, element);
    const target = path.join(to, element);
    const stat = fs.lstatSync(source);

    if (stat.isFile()) {
      fs.copyFileSync(source, target);
    } else if (stat.isDirectory()) {
      copyFolderSync(source, target);
    }
  }
}

function copyFileSync(source, target, options = {}) {
  assertExists(source);
  ensureDir(path.dirname(target));

  if (options.skipIfExists && fs.existsSync(target)) {
    console.log(`[略過] 已存在，未覆蓋: ${target}`);
    return;
  }

  fs.copyFileSync(source, target);
  console.log(`[成功] 已複製: ${target}`);
}

try {
  console.log('正在安裝 Gemini Review Gate...');


  copyFolderSync(sourceSkillDir, targetCodexSkillDir);
  console.log(`[成功] Codex Skill 已部署至: ${targetCodexSkillDir}`);

  copyFileSync(sourceReviewScript, path.join(targetCodexReviewScriptsDir, 'gemini_review.py'));
  copyFileSync(sourceStopHook, path.join(targetCodexHooksDir, 'stop_review_gate.py'));
  copyFileSync(sourceHooksExample, path.join(targetCodexDir, 'hooks.json'), { skipIfExists: true });
  copyFileSync(sourceSecretsExample, path.join(targetCodexDir, 'gemini-review.secrets.json'), { skipIfExists: true });
  copyFileSync(sourceAgents, path.join(targetCodexDir, 'AGENTS.md'), { skipIfExists: true });

  console.log('');
  console.log('Gemini Review Gate 安裝完成。');
  console.log('後續請確認:');
  console.log(`- ${path.join(targetCodexDir, 'gemini-review.secrets.json')} 已填入正確 backend 設定`);
  console.log(`- ${path.join(targetCodexDir, 'hooks.json')} 的 command 可在本機執行`);
  console.log('- 重新啟動 Codex 後再使用。');
} catch (error) {
  console.error('安裝過程中發生錯誤:', error.message);
  process.exitCode = 1;
}


