// PDF Export functionality
async function downloadChat() {
    const { jsPDF } = window.jspdf;
    
    try {
        const pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'pt',
            format: 'a4'
        });
        
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 40;
        const maxWidth = pageWidth - (margin * 2);
        let yPos = margin;
        
        // Title
        pdf.setFontSize(20);
        pdf.setFont(undefined, 'bold');
        const title = 'AI ChatBot - Lịch sử trò chuyện';
        await addTextAsImage(pdf, title, 20, true, margin, yPos, maxWidth);
        yPos += 40;
        
        // Date
        pdf.setFontSize(12);
        const dateStr = new Date().toLocaleString('vi-VN');
        await addTextAsImage(pdf, dateStr, 12, false, margin, yPos, maxWidth);
        yPos += 30;
        
        // Process messages
        const messages = chatContainer.querySelectorAll('.message');
        
        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            const isUser = msg.classList.contains('user');
            const content = msg.querySelector('.message-content');
            
            // Check if need new page
            if (yPos > pageHeight - 100) {
                pdf.addPage();
                yPos = margin;
            }
            
            // Message header
            const header = isUser ? '👤 Bạn:' : '🤖 AI:';
            pdf.setFontSize(14);
            await addTextAsImage(pdf, header, 14, true, margin, yPos, maxWidth);
            yPos += 25;
            
            // Message content (text)
            const textContent = content.textContent || content.innerText;
            pdf.setFontSize(11);
            
            // Split text into lines
            const words = textContent.split(' ');
            let line = '';
            
            for (let j = 0; j < words.length; j++) {
                const testLine = line + words[j] + ' ';
                const testWidth = pdf.getTextWidth(testLine);
                
                if (testWidth > maxWidth && j > 0) {
                    await addTextAsImage(pdf, line.trim(), 11, false, margin, yPos, maxWidth);
                    yPos += 18;
                    line = words[j] + ' ';
                    
                    // Check page break
                    if (yPos > pageHeight - 100) {
                        pdf.addPage();
                        yPos = margin;
                    }
                } else {
                    line = testLine;
                }
            }
            
            if (line.trim()) {
                await addTextAsImage(pdf, line.trim(), 11, false, margin, yPos, maxWidth);
                yPos += 18;
            }
            
            // Process images in message
            const images = msg.querySelectorAll('img');
            
            for (let k = 0; k < images.length; k++) {
                const img = images[k];
                
                try {
                    // Check page space for image
                    if (yPos > pageHeight - 300) {
                        pdf.addPage();
                        yPos = margin;
                    }
                    
                    yPos += 10;
                    
                    // Convert image to canvas
                    const canvas = await html2canvas(img, {
                        scale: 2,
                        logging: false,
                        useCORS: true
                    });
                    
                    const imgData = canvas.toDataURL('image/png');
                    const imgWidth = Math.min(maxWidth, 400);
                    const imgHeight = (canvas.height * imgWidth) / canvas.width;
                    
                    // Add image to PDF
                    pdf.addImage(imgData, 'PNG', margin, yPos, imgWidth, imgHeight);
                    yPos += imgHeight + 10;
                    
                    // Extract and render metadata
                    const metadataDiv = img.closest('.message')?.querySelector('div[style*="background: rgba(76, 175, 80"]');
                    
                    if (metadataDiv) {
                        const metadataText = metadataDiv.textContent || metadataDiv.innerText;
                        const cleanMetadata = metadataText
                            .replace(/\s+/g, ' ')
                            .replace(/📝|❌|🖼️|🎲|💾|⚙️/g, '')
                            .trim();
                        
                        if (cleanMetadata) {
                            pdf.setFontSize(9);
                            await addTextAsImage(pdf, cleanMetadata, 9, false, margin, yPos, maxWidth);
                            yPos += 15;
                        }
                    }
                    
                } catch (imgError) {
                    console.error('Error processing image:', imgError);
                    await addTextAsImage(pdf, '[Không thể tải ảnh]', 9, false, margin, yPos, maxWidth);
                    yPos += 15;
                }
            }
            
            yPos += 20; // Space between messages
        }
        
        // Save PDF
        const filename = `chat_${new Date().getTime()}.pdf`;
        pdf.save(filename);
        
        console.log('PDF exported successfully:', filename);
        
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('❌ Lỗi khi tạo PDF: ' + error.message);
    }
}

// Helper function to render text as image in PDF (for Unicode support)
async function addTextAsImage(pdf, text, fontSize, isBold, xPos, yPos, maxWidth) {
    return new Promise((resolve) => {
        // Create temporary canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = maxWidth * 2; // Higher resolution
        canvas.height = fontSize * 3;
        
        // Set font
        ctx.font = `${isBold ? 'bold' : 'normal'} ${fontSize * 2}px Arial`;
        ctx.fillStyle = '#000000';
        ctx.textBaseline = 'top';
        
        // Draw text
        ctx.fillText(text, 0, 0);
        
        // Convert to image
        const imgData = canvas.toDataURL('image/png');
        
        // Add to PDF
        pdf.addImage(imgData, 'PNG', xPos, yPos, maxWidth, fontSize);
        
        resolve();
    });
}

// Initialize download button
document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadChat);
    }
});
