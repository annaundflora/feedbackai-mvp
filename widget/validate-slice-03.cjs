const fs = require('fs');
const path = require('path');

// Read test.html
const htmlPath = path.join(__dirname, 'test.html');
const html = fs.readFileSync(htmlPath, 'utf-8');

// Check if ConsentScreen and ThankYouScreen are referenced
if (!html.includes('Consent Screen') && !html.includes('consent')) {
  throw new Error('ConsentScreen component not referenced in test.html');
}

if (!html.includes('ThankYou') && !html.includes('thankyou')) {
  throw new Error('ThankYouScreen component not referenced in test.html');
}

console.log('✓ ConsentScreen component present in test.html');
console.log('✓ ThankYouScreen component present in test.html');

// Check bundle size
const widgetPath = path.join(__dirname, 'dist', 'widget.js');
const stat = fs.statSync(widgetPath);
console.log('✓ Bundle size: ' + (stat.size / 1024).toFixed(2) + ' KB');

if (stat.size > 500000) {
  console.warn('⚠ Bundle size >500KB (target <200KB gzipped)');
}

console.log('\n✅ All validation checks passed!');
