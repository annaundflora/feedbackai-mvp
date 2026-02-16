#!/usr/bin/env node
/**
 * Post-build script: Copy test.html to dist and inject CSS link
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const widgetDir = path.resolve(__dirname, '..')
const distDir = path.join(widgetDir, 'dist')
const assetsDir = path.join(distDir, 'assets')

// Find CSS file in assets
const cssFiles = fs.readdirSync(assetsDir).filter(f => f.endsWith('.css'))
if (cssFiles.length === 0) {
  console.warn('⚠️  No CSS file found in dist/assets')
  process.exit(0)
}

const cssFile = cssFiles[0]
console.log(`✓ Found CSS: ${cssFile}`)

// Read test.html
const testHtmlPath = path.join(widgetDir, 'test.html')
let html = fs.readFileSync(testHtmlPath, 'utf-8')

// Replace script path and add CSS link
html = html.replace('./dist/widget.js', './widget.js')
html = html.replace(
  '<title>',
  `<link rel="stylesheet" href="./assets/${cssFile}">\n  <title>`
)

// Write to dist/index.html
fs.writeFileSync(path.join(distDir, 'index.html'), html)
console.log('✓ Created dist/index.html with CSS link')
