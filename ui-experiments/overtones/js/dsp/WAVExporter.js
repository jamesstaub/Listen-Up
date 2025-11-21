/**
 * WAV EXPORTER CLASS
 * Handles WAV file creation and download functionality
 */

export class WAVExporter {
    /**
     * Exports audio buffer data as a downloadable WAV file
     * @param {Float32Array} buffer - Audio buffer to export
     * @param {number} sampleRate - Sample rate for the WAV file
     * @param {string} filename - Filename for the download
     * @param {number} numCycles - Number of cycles to repeat the buffer
     */
    static exportAsWAV(buffer, sampleRate, filename, numCycles = 1) {
        if (buffer.length === 0) {
            throw new Error("Cannot export empty waveform data.");
        }
        
        const fullBuffer = WAVExporter.repeatBuffer(buffer, numCycles);
        const arrayBuffer = WAVExporter.createWAVBuffer(fullBuffer, sampleRate);
        WAVExporter.downloadFile(arrayBuffer, filename);
    }
    
    /**
     * Repeats a buffer for the specified number of cycles
     * @param {Float32Array} buffer - Original buffer
     * @param {number} numCycles - Number of cycles to repeat
     * @returns {Float32Array} Extended buffer
     */
    static repeatBuffer(buffer, numCycles) {
        const cycleLength = buffer.length;
        const totalLength = cycleLength * numCycles;
        const fullBuffer = new Float32Array(totalLength);
        
        for (let i = 0; i < totalLength; i++) {
            fullBuffer[i] = buffer[i % cycleLength];
        }
        
        return fullBuffer;
    }
    
    /**
     * Creates a WAV file buffer from audio data
     * @param {Float32Array} buffer - Audio buffer
     * @param {number} sampleRate - Sample rate
     * @returns {DataView} WAV file buffer as DataView
     */
    static createWAVBuffer(buffer, sampleRate) {
        const bufferLen = buffer.length;
        const numOfChan = 1; // Mono
        const bytesPerSample = 2; // 16-bit
        const blockAlign = numOfChan * bytesPerSample;
        const byteRate = sampleRate * blockAlign;
        const dataSize = bufferLen * bytesPerSample;
        const fileSize = 36 + dataSize;
        
        const arrayBuffer = new ArrayBuffer(fileSize + 8);
        const view = new DataView(arrayBuffer);

        // Write RIFF chunk
        WAVExporter.writeString(view, 0, 'RIFF');
        view.setUint32(4, fileSize, true); // Little-endian
        WAVExporter.writeString(view, 8, 'WAVE');

        // Write FMT chunk
        WAVExporter.writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);          // Sub-chunk size
        view.setUint16(20, 1, true);           // PCM format
        view.setUint16(22, numOfChan, true);   // Mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, byteRate, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, 16, true);          // 16 bits per sample

        // Write DATA chunk
        WAVExporter.writeString(view, 36, 'data');
        view.setUint32(40, dataSize, true);

        // Write the actual audio data (converted to 16-bit integer)
        let offset = 44;
        for (let i = 0; i < bufferLen; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, buffer[i]));
            view.setInt16(offset, s * 0x7FFF, true);
        }

        return view;
    }
    
    /**
     * Writes a string to a DataView at the specified offset
     * @param {DataView} view - DataView to write to
     * @param {number} offset - Byte offset to start writing
     * @param {string} string - String to write
     */
    static writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }
    
    /**
     * Downloads a file buffer as a blob
     * @param {DataView} arrayBuffer - File data as DataView
     * @param {string} filename - Filename for the download
     */
    static downloadFile(arrayBuffer, filename) {
        const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up the URL object
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }
    
    /**
     * Creates WAV file data and returns it as a Blob (for further processing)
     * @param {Float32Array} buffer - Audio buffer
     * @param {number} sampleRate - Sample rate
     * @param {number} numCycles - Number of cycles to repeat
     * @returns {Blob} WAV file as Blob
     */
    static createWAVBlob(buffer, sampleRate, numCycles = 1) {
        const fullBuffer = WAVExporter.repeatBuffer(buffer, numCycles);
        const wavBuffer = WAVExporter.createWAVBuffer(fullBuffer, sampleRate);
        return new Blob([wavBuffer], { type: 'audio/wav' });
    }
}