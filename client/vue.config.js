// Read in .env file.
const process = require('process');
const path = require('path');
const VuetifyLoaderPlugin = require('vuetify-loader/lib/plugin');
require('dotenv').config({
  path: path.resolve('..', '.env'),
});

// Grab the port to proxy to.
const flask_serve_port = process.env.FLASK_SERVE_PORT || 5000;

module.exports = {
  configureWebpack: {
    plugins: [
      new VuetifyLoaderPlugin(),
    ],
  },
  devServer: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${flask_serve_port}`,
        changeOrigin: true,
        pathRewrite: {
          '^/api': '',
        },
      }
    }
  }
};
