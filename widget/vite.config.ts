import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/main.tsx'),
      name: 'FeedbackAIWidget',
      formats: ['iife'],
      fileName: () => 'widget.js'
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        assetFileNames: (assetInfo) => {
          // Don't extract CSS - it will be inlined in the JS
          if (assetInfo.name === 'style.css') {
            return 'assets/[name].[ext]'
          }
          return 'assets/[name].[hash].[ext]'
        }
      }
    },
    cssCodeSplit: false,
    minify: 'esbuild',
    sourcemap: false
  }
})
