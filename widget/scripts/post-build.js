#!/usr/bin/env node
/**
 * Post-build script: Embed CSS into widget.js (self-injecting style tag)
 * and create dist/index.html for static serving.
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

// Read CSS content
const cssContent = fs.readFileSync(path.join(assetsDir, cssFile), 'utf-8')

// Create CSS self-injection snippet (prepended to widget.js)
// Uses a unique ID to prevent duplicate injection on multiple script loads
const cssInjection = `(function(){if(document.getElementById('feedbackai-styles'))return;var s=document.createElement('style');s.id='feedbackai-styles';s.textContent=${JSON.stringify(cssContent)};document.head.appendChild(s);})();`

// Embed CSS into widget.js
const widgetJsPath = path.join(distDir, 'widget.js')
const widgetJs = fs.readFileSync(widgetJsPath, 'utf-8')
fs.writeFileSync(widgetJsPath, cssInjection + '\n' + widgetJs)
console.log('✓ Embedded CSS into widget.js (self-injecting)')

// Create dist/index.html for static serving (no separate CSS needed)
const testHtmlPath = path.join(widgetDir, 'test.html')
let html = fs.readFileSync(testHtmlPath, 'utf-8')
html = html.replace('./dist/widget.js', './widget.js')
fs.writeFileSync(path.join(distDir, 'index.html'), html)
console.log('✓ Created dist/index.html')
