// Cut evenly spaced still frames from a video with AVFoundation, for Macs without ffmpeg.
//
//   swift scripts/video_frames.swift <video> <out dir> <count> <max side>
//
// Frames are upright (the video's rotation is applied), at most <max side> px on their long side,
// written as 00001.jpg, 00002.jpg, ... Prints the number written. Used by scripts/build_room.py.

import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 5, let count = Int(args[3]), let maxSide = Double(args[4]), count > 0 else {
    FileHandle.standardError.write("usage: video_frames.swift <video> <out dir> <count> <max side>\n".data(using: .utf8)!)
    exit(2)
}
let video = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2], isDirectory: true)

let asset = AVURLAsset(url: video)
let seconds = CMTimeGetSeconds(asset.duration)
guard seconds.isFinite, seconds > 0 else {
    FileHandle.standardError.write("cannot read \(video.path) as a video\n".data(using: .utf8)!)
    exit(1)
}

let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.maximumSize = CGSize(width: maxSide, height: maxSide)
// A frame within a tenth of a step of the asked time is as good, and much faster to decode.
let step = seconds / Double(count)
let tolerance = CMTime(seconds: step / 10, preferredTimescale: 600)
generator.requestedTimeToleranceBefore = tolerance
generator.requestedTimeToleranceAfter = tolerance

var written = 0
for k in 0..<count {
    let time = CMTime(seconds: (Double(k) + 0.5) * step, preferredTimescale: 600)
    guard let image = try? generator.copyCGImage(at: time, actualTime: nil) else { continue }
    let url = outDir.appendingPathComponent(String(format: "%05d.jpg", written + 1))
    guard let destination = CGImageDestinationCreateWithURL(
        url as CFURL, UTType.jpeg.identifier as CFString, 1, nil
    ) else { continue }
    CGImageDestinationAddImage(
        destination, image, [kCGImageDestinationLossyCompressionQuality: 0.92] as CFDictionary
    )
    if CGImageDestinationFinalize(destination) { written += 1 }
}
print(written)
exit(written > 0 ? 0 : 1)
