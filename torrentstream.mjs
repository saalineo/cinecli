#!/usr/bin/env node
import WebTorrent from '/usr/lib/webtorrent-cli/node_modules/webtorrent/index.js'
import http from 'http'
import fs from 'fs'

const mg = process.argv[2]
const mode = process.argv[3] || 'stream'
const outdir = process.argv[4] || '/tmp'

if (!mg) {
  process.stderr.write('usage: torrentstream.mjs <magnet> [stream|download] [outdir]\n')
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

  const pick = files.find(f =>
    /\.(mp4|mkv|webm|avi|mov)$/i.test(f.name) && !/sample/i.test(f.name)
  ) || files[0]

  if (mode === 'stream') {
    const file = torrent.files[pick.i]
    file.select()

    const ext = pick.name.match(/\.(\w+)$/)?.[1]?.toLowerCase()
    const mime = ext === 'mkv' ? 'video/x-matroska'
      : ext === 'webm' ? 'video/webm'
      : ext === 'avi' ? 'video/x-msvideo'
      : ext === 'mov' ? 'video/quicktime'
      : 'video/mp4'

    const server = http.createServer((req, res) => {
      const range = req.headers.range
      const size = file.length

      const stream = range
        ? (() => {
            const parts = range.replace(/bytes=/, '').split('-')
            const start = parts[0] ? parseInt(parts[0], 10) : size - parseInt(parts[1], 10)
            const end = parts[1] ? parseInt(parts[1], 10) : size - 1
            const len = end - start + 1
            res.writeHead(206, {
              'Content-Range': `bytes ${start}-${end}/${size}`,
              'Content-Type': mime,
              'Content-Length': len,
              'Accept-Ranges': 'bytes'
            })
            return file.createReadStream({ start, end })
          })()
        : (() => {
            res.writeHead(200, {
              'Content-Type': mime,
              'Content-Length': size,
              'Accept-Ranges': 'bytes'
            })
            return file.createReadStream()
          })()

      stream.pipe(res)
      res.on('close', () => {
        stream.destroy()
      })
      stream.on('error', () => {})
    })

    server.on('clientError', () => {})

    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      fs.writeSync(1, `${port}\n`)
      process.stderr.write(`streaming: ${pick.name}\n`)
    })
  } else {
    process.stdout.write(`${outdir}/${pick.name}\n`)
    torrent.files[pick.i].select()
  }
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
