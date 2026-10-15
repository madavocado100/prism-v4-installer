// Test the same static app over its documented localhost serving path.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
exports.start = async function () {
  const html = fs.readFileSync(path.resolve(__dirname, '../rgb-audio-visualizer-v4.html'));
  const server = http.createServer((request, response) => {
    response.writeHead(200, {'Content-Type':'text/html; charset=utf-8','Content-Length':html.length});
    response.end(html);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  return {url:`http://127.0.0.1:${server.address().port}/`,close:()=>new Promise(resolve=>server.close(resolve))};
};
