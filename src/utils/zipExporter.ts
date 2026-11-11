import JSZip from 'jszip';
import { REPO_FILES } from '../data/repoFiles';

export async function downloadIntegrationZip(): Promise<void> {
  const zip = new JSZip();

  // Add all files into the zip archive matching the exact repository tree
  for (const file of REPO_FILES) {
    zip.file(file.path, file.content);
  }

  // Generate the zip blob
  const content = await zip.generateAsync({
    type: 'blob',
    compression: 'DEFLATE',
    compressionOptions: {
      level: 9,
    },
  });

  // Create download link and trigger download
  const blobUrl = URL.createObjectURL(content);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = 'welock-home-assistant-hacs-v2.0.0.zip';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(blobUrl);
}
