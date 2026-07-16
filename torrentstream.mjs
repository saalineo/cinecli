#!/usr/bin/env node
import WebTorrent from '/usr/lib/webtorrent-cli/node_modules/webtorrent/index.js'

const mg = process.argv[2]
const outdir = process.argv[3] || '/tmp'

if (!mg) {
  process.stderr.write('usage: torrentstream.mjs <magnet> [outdir]\n')
  process.exit(1)
}

const client = new WebTorrent({
  dht: {
    bootstrap: [
      'router.bittorrent.com:6881',
      'dht.transmissionbt.com:6881',
      'router.utorrent.com:6881',
      'dht.aelitis.com:6881',
      '67.215.246.10:6881',
      '82.221.103.244:6881',
      '212.129.33.59:6881',
      '87.98.162.88:6881'
    ],
    host: '0.0.0.0'
  }
})

client.on('error', err => {
  process.stderr.write(`client error: ${err.message}\n`)
})
client.on('warning', err => {
  process.stderr.write(`client warning: ${err.message}\n`)
})

const torrent = client.add(mg, { path: outdir })

torrent.on('error', err => {
  process.stderr.write(`torrent error: ${err.message}\n`)
})
torrent.on('warning', err => {
  process.stderr.write(`torrent warning: ${err.message}\n`)
})

torrent.on('infoHash', () => {
  process.stderr.write(`infohash: ${torrent.infoHash}\n`)
})

torrent.on('metadata', () => {
  const files = torrent.files
    .map((f, i) => ({ i, name: f.name, len: f.length }))
    .sort((a, b) => b.len - a.len)

  // pick largest media file
  const pick = files.find(f =>
    /\.(mp4|mkv|webm|avi|mov)$/i.test(f.name) && !/sample/i.test(f.name)
  ) || files[0]

  process.stdout.write(`${outdir}/${pick.name}\n`)

  torrent.files[pick.i].select()
})

torrent.on('done', () => {
  process.stderr.write('download complete\n')
  client.destroy()
})

const cleanup = () => {
  process.stderr.write('\nstopping...\n')
  client.destroy()
  process.exit(1)
}
process.on('SIGINT', cleanup)
process.on('SIGTERM', cleanup)

setInterval(() => {
  const prog = torrent.progress != null ? (torrent.progress * 100).toFixed(1) : '?'
  const peers = torrent.numPeers ?? 0
  const down = ((torrent.downloadSpeed || 0) / 1e6).toFixed(1)
  process.stderr.write(`\r  ${prog}%  ↓ ${down} MB/s  peers: ${peers}     `)
}, 2000)
