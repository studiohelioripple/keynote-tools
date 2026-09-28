#!/usr/bin/env swift
import Foundation
import AppKit
import Vision
import CoreImage
import CoreGraphics

struct BackgroundColorResult: Codable {
    let dominantRGB: [Int]         // 0..255
    let keynoteRGB: [Int]          // 0..65535
    let hex: String                // #RRGGBB
    let isGradient: Bool
    let gradientVariance: Double
    let noiseVariance: Double
    let planeParamsR: [Double]     // a, b, c
    let planeParamsG: [Double]     // a, b, c
    let planeParamsB: [Double]     // a, b, c
}

struct CropAndHealResult: Codable {
    let success: Bool
    let imageWidth: Int
    let imageHeight: Int
    let box: [Int]                 // x, y, w, h
    let background: BackgroundColorResult
    let textDetected: [String]
    let cropPathBefore: String?
    let cropPathAfter: String?
    let outputPath: String?
}

// MARK: - Image Utilities

func loadCGImage(from path: String) -> CGImage? {
    let url = URL(fileURLWithPath: path)
    guard let nsImage = NSImage(contentsOf: url) else { return nil }
    return nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil)
}

func saveCGImage(_ cgImage: CGImage, to path: String, format: CFString = "public.png" as CFString) -> Bool {
    let url = URL(fileURLWithPath: path) as CFURL
    guard let destination = CGImageDestinationCreateWithURL(url, format, 1, nil) else { return false }
    CGImageDestinationAddImage(destination, cgImage, nil)
    return CGImageDestinationFinalize(destination)
}

// MARK: - Crop Sub-Image

func cropImage(_ cgImage: CGImage, rect: CGRect) -> CGImage? {
    let imgW = CGFloat(cgImage.width)
    let imgH = CGFloat(cgImage.height)
    let clampedRect = CGRect(
        x: max(0, min(imgW - 1, rect.origin.x)),
        y: max(0, min(imgH - 1, rect.origin.y)),
        width: max(1, min(imgW - rect.origin.x, rect.width)),
        height: max(1, min(imgH - rect.origin.y, rect.height))
    )
    return cgImage.cropping(to: clampedRect)
}

// MARK: - Background Color & 2D Gradient Extraction

func analyzePerimeterBackground(
    cgImage: CGImage,
    box: CGRect,
    margin: Int = 14
) -> BackgroundColorResult {
    let width = cgImage.width
    let height = cgImage.height
    
    let bx = Int(box.origin.x)
    let by = Int(box.origin.y)
    let bw = Int(box.width)
    let bh = Int(box.height)
    
    let x1 = max(0, min(width - 1, bx))
    let y1 = max(0, min(height - 1, by))
    let x2 = max(x1 + 1, min(width, bx + bw))
    let y2 = max(y1 + 1, min(height, by + bh))
    
    let outerY1 = max(0, y1 - margin)
    let outerY2 = min(height, y2 + margin)
    let outerX1 = max(0, x1 - margin)
    let outerX2 = min(width, x2 + margin)
    
    guard let dataProvider = cgImage.dataProvider,
          let data = dataProvider.data,
          let ptr = CFDataGetBytePtr(data) else {
        return BackgroundColorResult(
            dominantRGB: [128, 128, 128],
            keynoteRGB: [32768, 32768, 32768],
            hex: "#808080",
            isGradient: false,
            gradientVariance: 0,
            noiseVariance: 0,
            planeParamsR: [0, 0, 128],
            planeParamsG: [0, 0, 128],
            planeParamsB: [0, 0, 128]
        )
    }
    
    let bytesPerRow = cgImage.bytesPerRow
    let bpp = cgImage.bitsPerPixel / 8
    
    var coordsX: [Double] = []
    var coordsY: [Double] = []
    var rVals: [Double] = []
    var gVals: [Double] = []
    var bVals: [Double] = []
    
    func samplePixel(x: Int, y: Int) {
        let offset = y * bytesPerRow + x * bpp
        let r = Double(ptr[offset])
        let g = Double(ptr[offset + 1])
        let b = Double(ptr[offset + 2])
        coordsX.append(Double(x))
        coordsY.append(Double(y))
        rVals.append(r)
        gVals.append(g)
        bVals.append(b)
    }
    
    // Top strip
    for y in outerY1..<y1 {
        for x in outerX1..<outerX2 { samplePixel(x: x, y: y) }
    }
    // Bottom strip
    for y in y2..<outerY2 {
        for x in outerX1..<outerX2 { samplePixel(x: x, y: y) }
    }
    // Left strip
    for y in y1..<y2 {
        for x in outerX1..<x1 { samplePixel(x: x, y: y) }
    }
    // Right strip
    for y in y1..<y2 {
        for x in x2..<outerX2 { samplePixel(x: x, y: y) }
    }
    
    if rVals.isEmpty {
        return BackgroundColorResult(
            dominantRGB: [128, 128, 128],
            keynoteRGB: [32768, 32768, 32768],
            hex: "#808080",
            isGradient: false,
            gradientVariance: 0,
            noiseVariance: 0,
            planeParamsR: [0, 0, 128],
            planeParamsG: [0, 0, 128],
            planeParamsB: [0, 0, 128]
        )
    }
    
    let sortedR = rVals.sorted()
    let sortedG = gVals.sorted()
    let sortedB = bVals.sorted()
    let mid = sortedR.count / 2
    let medR = Int(sortedR[mid])
    let medG = Int(sortedG[mid])
    let medB = Int(sortedB[mid])
    
    let meanR = rVals.reduce(0, +) / Double(rVals.count)
    let varR = rVals.map { pow($0 - meanR, 2) }.reduce(0, +) / Double(rVals.count)
    let isGrad = varR > 8.0
    
    func fitPlane(values: [Double]) -> [Double] {
        let n = Double(coordsX.count)
        var sumX = 0.0, sumY = 0.0, sumX2 = 0.0, sumY2 = 0.0, sumXY = 0.0
        var sumV = 0.0, sumXV = 0.0, sumYV = 0.0
        
        for i in 0..<coordsX.count {
            let x = coordsX[i]
            let y = coordsY[i]
            let v = values[i]
            sumX += x; sumY += y
            sumX2 += x * x; sumY2 += y * y; sumXY += x * y
            sumV += v; sumXV += x * v; sumYV += y * v
        }
        
        let det = sumX2 * (sumY2 * n - sumY * sumY) - sumXY * (sumXY * n - sumX * sumY) + sumX * (sumXY * sumY - sumX * sumY2)
        if abs(det) < 1e-7 {
            return [0.0, 0.0, sumV / n]
        }
        
        let a = ((sumXV * (sumY2 * n - sumY * sumY)) - (sumXY * (sumYV * n - sumV * sumY)) + (sumX * (sumYV * sumY - sumV * sumY2))) / det
        let b = ((sumX2 * (sumYV * n - sumV * sumY)) - (sumXV * (sumXY * n - sumX * sumY)) + (sumX * (sumXY * sumV - sumX * sumYV))) / det
        let c = ((sumX2 * (sumY2 * sumV - sumY * sumYV)) - (sumXY * (sumXY * sumV - sumX * sumYV)) + (sumXV * (sumXY * sumY - sumX * sumY2))) / det
        
        return [a, b, c]
    }
    
    let planeR = fitPlane(values: rVals)
    let planeG = fitPlane(values: gVals)
    let planeB = fitPlane(values: bVals)
    
    var sumSqRes = 0.0
    for i in 0..<coordsX.count {
        let x = coordsX[i]
        let y = coordsY[i]
        let predR = planeR[0] * x + planeR[1] * y + planeR[2]
        sumSqRes += pow(rVals[i] - predR, 2)
    }
    let noiseVar = sumSqRes / Double(coordsX.count)
    
    let kR = min(65535, max(0, Int(Double(medR) * 257.0)))
    let kG = min(65535, max(0, Int(Double(medG) * 257.0)))
    let kB = min(65535, max(0, Int(Double(medB) * 257.0)))
    let hexStr = String(format: "#%02X%02X%02X", medR, medG, medB)
    
    return BackgroundColorResult(
        dominantRGB: [medR, medG, medB],
        keynoteRGB: [kR, kG, kB],
        hex: hexStr,
        isGradient: isGrad,
        gradientVariance: varR,
        noiseVariance: noiseVar,
        planeParamsR: planeR,
        planeParamsG: planeG,
        planeParamsB: planeB
    )
}

// MARK: - Apple Vision Text & Artifact Detection

func detectTextInCrop(cropImage: CGImage) -> [String] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    
    let handler = VNImageRequestHandler(cgImage: cropImage, options: [:])
    do {
        try handler.perform([request])
        let observations = request.results ?? []
        return observations.compactMap { $0.topCandidates(1).first?.string }
    } catch {
        return []
    }
}

// MARK: - Pure Synthesized Background Patch Generator (Zero Artifacts)

func generatePureBackgroundPatch(
    box: CGRect,
    bgAnalysis: BackgroundColorResult
) -> CGImage? {
    let bw = max(1, Int(box.width))
    let bh = max(1, Int(box.height))
    let bx = Int(box.origin.x)
    let by = Int(box.origin.y)
    
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let bytesPerPixel = 4
    let bytesPerRow = bw * bytesPerPixel
    
    guard let context = CGContext(
        data: nil,
        width: bw,
        height: bh,
        bitsPerComponent: 8,
        bytesPerRow: bytesPerRow,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ), let dataPtr = context.data?.bindMemory(to: UInt8.self, capacity: bh * bytesPerRow) else {
        return nil
    }
    
    let pR = bgAnalysis.planeParamsR
    let pG = bgAnalysis.planeParamsG
    let pB = bgAnalysis.planeParamsB
    
    // N = sqrt(3 * variance) for uniform distribution to match variance
    let noiseAmp = min(sqrt(bgAnalysis.noiseVariance) * 1.732, 40.0)
    
    for ly in 0..<bh {
        let gy = by + ly
        for lx in 0..<bw {
            let gx = bx + lx
            
            var r = pR[0] * Double(gx) + pR[1] * Double(gy) + pR[2]
            var g = pG[0] * Double(gx) + pG[1] * Double(gy) + pG[2]
            var b = pB[0] * Double(gx) + pB[1] * Double(gy) + pB[2]
            
            if noiseAmp > 0.5 {
                let noise = Double.random(in: -noiseAmp...noiseAmp)
                r += noise
                g += noise
                b += noise
            }
            
            r = min(255.0, max(0.0, r))
            g = min(255.0, max(0.0, g))
            b = min(255.0, max(0.0, b))
            
            let offset = ly * bytesPerRow + lx * bytesPerPixel
            dataPtr[offset] = UInt8(r)
            dataPtr[offset + 1] = UInt8(g)
            dataPtr[offset + 2] = UInt8(b)
            dataPtr[offset + 3] = 255
        }
    }
    
    return context.makeImage()
}

// MARK: - Healing Brush / Background Inpainting Engine (With Correct Coordinates)

func healCropAndSplice(
    fullImage: CGImage,
    box: CGRect,
    bgAnalysis: BackgroundColorResult,
    featherRadius: Int = 3
) -> CGImage? {
    let width = fullImage.width
    let height = fullImage.height
    
    let bx = Int(box.origin.x)
    let by = Int(box.origin.y)
    let bw = Int(box.width)
    let bh = Int(box.height)
    
    let x1 = max(0, min(width - 1, bx))
    let y1 = max(0, min(height - 1, by))
    let x2 = max(x1 + 1, min(width, bx + bw))
    let y2 = max(y1 + 1, min(height, by + bh))
    
    let boxW = x2 - x1
    let boxH = y2 - y1
    
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let bytesPerPixel = 4
    let bytesPerRow = width * bytesPerPixel
    guard let context = CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: bytesPerRow,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { return nil }
    
    // Draw original image into context
    context.draw(fullImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    
    guard let dataPtr = context.data?.bindMemory(to: UInt8.self, capacity: height * bytesPerRow) else {
        return nil
    }
    
    let pR = bgAnalysis.planeParamsR
    let pG = bgAnalysis.planeParamsG
    let pB = bgAnalysis.planeParamsB
    let noiseAmp = min(sqrt(bgAnalysis.noiseVariance) * 1.732, 40.0)
    
    // CoreGraphics context.draw renders image into the context. We will modify the buffer directly.
    // For CGContext on macOS (without explicit CTM flips), Y=0 in the buffer is the top row.
    for localY in 0..<boxH {
        let globalY = y1 + localY
        let bufferY = globalY
        
        for localX in 0..<boxW {
            let globalX = x1 + localX
            
            var reconR = pR[0] * Double(globalX) + pR[1] * Double(globalY) + pR[2]
            var reconG = pG[0] * Double(globalX) + pG[1] * Double(globalY) + pG[2]
            var reconB = pB[0] * Double(globalX) + pB[1] * Double(globalY) + pB[2]
            
            if noiseAmp > 0.5 {
                let noise = Double.random(in: -noiseAmp...noiseAmp)
                reconR += noise
                reconG += noise
                reconB += noise
            }
            
            reconR = min(255.0, max(0.0, reconR))
            reconG = min(255.0, max(0.0, reconG))
            reconB = min(255.0, max(0.0, reconB))
            
            var weight = 1.0
            if featherRadius > 0 {
                let distLeft = Double(localX)
                let distRight = Double(boxW - 1 - localX)
                let distTop = Double(localY)
                let distBottom = Double(boxH - 1 - localY)
                let minDist = min(distLeft, distRight, distTop, distBottom)
                if minDist < Double(featherRadius) {
                    weight = (minDist + 1.0) / Double(featherRadius + 1)
                }
            }
            
            let pixelOffset = bufferY * bytesPerRow + globalX * bytesPerPixel
            let origR = Double(dataPtr[pixelOffset])
            let origG = Double(dataPtr[pixelOffset + 1])
            let origB = Double(dataPtr[pixelOffset + 2])
            
            let finalR = origR * (1.0 - weight) + reconR * weight
            let finalG = origG * (1.0 - weight) + reconG * weight
            let finalB = origB * (1.0 - weight) + reconB * weight
            
            dataPtr[pixelOffset] = UInt8(finalR)
            dataPtr[pixelOffset + 1] = UInt8(finalG)
            dataPtr[pixelOffset + 2] = UInt8(finalB)
            dataPtr[pixelOffset + 3] = 255
        }
    }
    
    return context.makeImage()
}

// MARK: - CLI Dispatcher

func printUsage() {
    let usage = """
    Keynote Apple Vision & CoreImage Healing Engine (keynote_healer)
    Usage:
      keynote_healer --extract-bg <image> --box <x,y,w,h>
      keynote_healer --crop <image> --box <x,y,w,h> --out <crop.png>
      keynote_healer --pure-patch <image> --box <x,y,w,h> --out <patch.png>
      keynote_healer --heal <image> --box <x,y,w,h> --out <healed.png> [--save-crop-before <path>] [--save-crop-after <path>]
    """
    fputs(usage + "\n", stderr)
}

func parseBox(_ str: String) -> CGRect? {
    let parts = str.split(separator: ",").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
    guard parts.count == 4 else { return nil }
    return CGRect(x: parts[0], y: parts[1], width: parts[2], height: parts[3])
}

let args = Array(CommandLine.arguments.dropFirst())
if args.isEmpty {
    printUsage()
    exit(1)
}

var mode = ""
var imagePath = ""
var boxRect: CGRect?
var outPath: String?
var cropBeforePath: String?
var cropAfterPath: String?

var i = 0
while i < args.count {
    let arg = args[i]
    if arg == "--extract-bg" {
        mode = "extract-bg"
        i += 1
        if i < args.count { imagePath = args[i] }
    } else if arg == "--crop" {
        mode = "crop"
        i += 1
        if i < args.count { imagePath = args[i] }
    } else if arg == "--pure-patch" {
        mode = "pure-patch"
        i += 1
        if i < args.count { imagePath = args[i] }
    } else if arg == "--heal" {
        mode = "heal"
        i += 1
        if i < args.count { imagePath = args[i] }
    } else if arg == "--box" {
        i += 1
        if i < args.count { boxRect = parseBox(args[i]) }
    } else if arg == "--out" {
        i += 1
        if i < args.count { outPath = args[i] }
    } else if arg == "--save-crop-before" {
        i += 1
        if i < args.count { cropBeforePath = args[i] }
    } else if arg == "--save-crop-after" {
        i += 1
        if i < args.count { cropAfterPath = args[i] }
    }
    i += 1
}

guard let cgImg = loadCGImage(from: imagePath) else {
    fputs("ERROR: Unable to load image at \(imagePath)\n", stderr)
    exit(1)
}

guard let targetBox = boxRect else {
    fputs("ERROR: Missing or invalid --box argument (expected 'x,y,w,h')\n", stderr)
    exit(1)
}

let bgResult = analyzePerimeterBackground(cgImage: cgImg, box: targetBox)

if mode == "extract-bg" {
    let encoder = JSONEncoder()
    encoder.outputFormatting = .prettyPrinted
    if let jsonData = try? encoder.encode(bgResult), let jsonStr = String(data: jsonData, encoding: .utf8) {
        print(jsonStr)
    }
    exit(0)
} else if mode == "crop" {
    guard let cropped = cropImage(cgImg, rect: targetBox), let dest = outPath else {
        fputs("ERROR: Failed to crop or missing --out\n", stderr)
        exit(1)
    }
    if saveCGImage(cropped, to: dest) {
        print("[✓] Saved crop to \(dest)")
    } else {
        fputs("ERROR: Failed to save cropped image\n", stderr)
        exit(1)
    }
    exit(0)
} else if mode == "pure-patch" {
    guard let patch = generatePureBackgroundPatch(box: targetBox, bgAnalysis: bgResult), let dest = outPath else {
        fputs("ERROR: Failed to generate pure patch\n", stderr)
        exit(1)
    }
    if saveCGImage(patch, to: dest) {
        print("[✓] Saved pure background patch to \(dest)")
    } else {
        fputs("ERROR: Failed to save pure patch\n", stderr)
        exit(1)
    }
    exit(0)
} else if mode == "heal" {
    if let cropBefore = cropBeforePath, let beforeCrop = cropImage(cgImg, rect: targetBox) {
        _ = saveCGImage(beforeCrop, to: cropBefore)
    }
    
    var textFound: [String] = []
    if let cropImg = cropImage(cgImg, rect: targetBox) {
        textFound = detectTextInCrop(cropImage: cropImg)
    }
    
    guard let healedImg = healCropAndSplice(fullImage: cgImg, box: targetBox, bgAnalysis: bgResult) else {
        fputs("ERROR: Failed to heal image\n", stderr)
        exit(1)
    }
    
    // Save clean pure patch or healed crop after
    if let cropAfter = cropAfterPath {
        if let purePatch = generatePureBackgroundPatch(box: targetBox, bgAnalysis: bgResult) {
            _ = saveCGImage(purePatch, to: cropAfter)
        }
    }
    
    let dest = outPath ?? imagePath
    if saveCGImage(healedImg, to: dest) {
        let res = CropAndHealResult(
            success: true,
            imageWidth: cgImg.width,
            imageHeight: cgImg.height,
            box: [Int(targetBox.origin.x), Int(targetBox.origin.y), Int(targetBox.width), Int(targetBox.height)],
            background: bgResult,
            textDetected: textFound,
            cropPathBefore: cropBeforePath,
            cropPathAfter: cropAfterPath,
            outputPath: dest
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        if let jsonData = try? encoder.encode(res), let jsonStr = String(data: jsonData, encoding: .utf8) {
            print(jsonStr)
        }
    } else {
        fputs("ERROR: Failed to save healed image\n", stderr)
        exit(1)
    }
}
