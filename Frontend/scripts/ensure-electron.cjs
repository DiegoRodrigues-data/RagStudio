/* eslint-disable */
// Postinstall safety net: on some setups (notably node_modules synced through
// Dropbox, or npm skipping nested lifecycle scripts) the `electron` package is
// installed without its binary (`node_modules/electron/dist`). This script
// re-runs Electron's own installer when the binary is missing.
const fs = require('fs')
const path = require('path')

const electronDir = path.join(__dirname, '..', 'node_modules', 'electron')
const pathTxt = path.join(electronDir, 'path.txt')
const installJs = path.join(electronDir, 'install.js')

if (!fs.existsSync(electronDir)) {
  process.exit(0)
}

let ok = false
if (fs.existsSync(pathTxt)) {
  const rel = fs.readFileSync(pathTxt, 'utf8').trim()
  ok = fs.existsSync(path.join(electronDir, 'dist', rel))
}

if (!ok && fs.existsSync(installJs)) {
  console.log(
    '[ensure-electron] Electron binary missing, running node_modules/electron/install.js ...'
  )
  const { spawnSync } = require('child_process')
  const r = spawnSync(process.execPath, [installJs], { stdio: 'inherit', cwd: electronDir })
  if (r.status !== 0) {
    console.warn(
      '[ensure-electron] install.js failed; try: rm -rf node_modules/electron && npm install electron'
    )
  }
}
