import { nodeResolve } from '@rollup/plugin-node-resolve';

export default {
  input: 'src/editor.js',
  output: {
    file: 'dist/editor.bundle.js',
    format: 'iife',
    name: 'CodeMirrorEditor'
  },
  plugins: [nodeResolve()]
};
