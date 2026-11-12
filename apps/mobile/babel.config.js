module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['@babel/preset-env', { targets: { node: 'current' } }],
      '@babel/preset-typescript',
      ['@babel/preset-react', { runtime: 'automatic' }],
    ],
    plugins: [
      'react-native-reanimated/plugin',
      ['module-resolver', { alias: { '@': './src', '@rest/api-client': '../packages/api-client' } }],
    ],
  };
};