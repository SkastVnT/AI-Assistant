/**
 * Export Handler Module
 * Handles chat export to PDF and other formats
 */

export class ExportHandler {
    constructor() {
        this.isExporting = false;
    }

    /**
     * Download chat as PDF
     * Uses jsPDF and html2canvas libraries
     */
    async downloadChatAsPDF(chatContainer, onProgress) {
        if (this.isExporting) {
            alert('Đang export, vui lòng đợi...');
            return;
        }

        const messages = Array.from(chatContainer.children);
        if (messages.length === 0) {
            alert('Chưa có lịch sử chat để tải xuống!');
            return;
        }

        this.isExporting = true;

        try {
            // Check if jsPDF is available
            if (typeof window.jspdf === 'undefined') {
                throw new Error('jsPDF library not loaded');
            }

            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF('p', 'mm', 'a4');
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 15;
            const maxWidth = pageWidth - (margin * 2);
            let yOffset = margin;

            // Helper function to add text as image (for Unicode support)
            const addTextAsImage = async (text, fontSize, isBold, xPos, yPos, maxW) => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                ctx.font = `${isBold ? 'bold' : 'normal'} ${fontSize}px Arial, sans-serif`;
                const metrics = ctx.measureText(text);
                const textWidth = metrics.width;
                
                canvas.width = Math.min(textWidth + 10, maxW * 3.78);
                canvas.height = fontSize * 1.5;
                
                ctx.font = `${isBold ? 'bold' : 'normal'} ${fontSize}px Arial, sans-serif`;
                ctx.fillStyle = '#000000';
                ctx.textBaseline = 'top';
                
                // Word wrap
                const words = text.split(' ');
                const lines = [];
                let currentLine = words[0];
                
                for (let i = 1; i < words.length; i++) {
                    const testLine = currentLine + ' ' + words[i];
                    const testWidth = ctx.measureText(testLine).width;
                    
                    if (testWidth > maxW * 3.78) {
                        lines.push(currentLine);
                        currentLine = words[i];
                    } else {
                        currentLine = testLine;
                    }
                }
                lines.push(currentLine);
                
                canvas.height = lines.length * fontSize * 1.5;
                ctx.font = `${isBold ? 'bold' : 'normal'} ${fontSize}px Arial, sans-serif`;
                ctx.fillStyle = '#000000';
                ctx.textBaseline = 'top';
                
                lines.forEach((line, idx) => {
                    ctx.fillText(line, 5, idx * fontSize * 1.5);
                });
                
                const imgData = canvas.toDataURL('image/png');
                const imgWidth = Math.min(maxW, canvas.width / 3.78);
                const imgHeight = canvas.height / 3.78;
                
                return { imgData, imgWidth, imgHeight, lineCount: lines.length };
            };

            // Title
            if (onProgress) onProgress('Tạo tiêu đề...');
            const titleData = await addTextAsImage('AI CHATBOT - LỊCH SỬ HỘI THOẠI', 24, true, 0, 0, maxWidth);
            pdf.addImage(titleData.imgData, 'PNG', (pageWidth - titleData.imgWidth) / 2, yOffset, titleData.imgWidth, titleData.imgHeight);
            yOffset += titleData.imgHeight + 5;

            // Timestamp
            const timestampText = 'Xuất lúc: ' + new Date().toLocaleString('vi-VN');
            const timestampData = await addTextAsImage(timestampText, 12, false, 0, 0, maxWidth);
            pdf.addImage(timestampData.imgData, 'PNG', (pageWidth - timestampData.imgWidth) / 2, yOffset, timestampData.imgWidth, timestampData.imgHeight);
            yOffset += timestampData.imgHeight + 10;

            // Process each message
            for (let i = 0; i < messages.length; i++) {
                if (onProgress) onProgress(`Xử lý tin nhắn ${i + 1}/${messages.length}...`);

                const msg = messages[i];
                const isUser = msg.classList.contains('user');
                const textEl = msg.querySelector('.message-text');
                const imageEl = msg.querySelector('img');

                // Check if need new page
                if (yOffset > pageHeight - 40) {
                    pdf.addPage();
                    yOffset = margin;
                }

                // Message header
                const header = isUser ? '👤 USER' : '🤖 AI';
                const headerData = await addTextAsImage(header, 14, true, 0, 0, maxWidth);
                pdf.addImage(headerData.imgData, 'PNG', margin, yOffset, headerData.imgWidth, headerData.imgHeight);
                yOffset += headerData.imgHeight + 3;

                // Message text
                if (textEl) {
                    const text = textEl.textContent || '';
                    const maxCharsPerChunk = 500;
                    const chunks = [];
                    
                    for (let j = 0; j < text.length; j += maxCharsPerChunk) {
                        chunks.push(text.substring(j, j + maxCharsPerChunk));
                    }

                    for (const chunk of chunks) {
                        const textData = await addTextAsImage(chunk, 12, false, 0, 0, maxWidth);
                        
                        if (yOffset + textData.imgHeight > pageHeight - margin) {
                            pdf.addPage();
                            yOffset = margin;
                        }
                        
                        pdf.addImage(textData.imgData, 'PNG', margin, yOffset, textData.imgWidth, textData.imgHeight);
                        yOffset += textData.imgHeight + 2;
                    }
                }

                // Handle images
                const allImages = msg.querySelectorAll('img');
                for (const imgEl of allImages) {
                    if (imgEl && imgEl.src) {
                        yOffset += 5;

                        try {
                            if (typeof html2canvas !== 'undefined') {
                                const canvas = await html2canvas(imgEl, {
                                    scale: 1,
                                    logging: false,
                                    backgroundColor: null
                                });

                                const imgData = canvas.toDataURL('image/jpeg', 0.7);
                                const imgWidth = Math.min(maxWidth, 100);
                                const imgHeight = (canvas.height * imgWidth) / canvas.width;

                                if (yOffset + imgHeight > pageHeight - margin) {
                                    pdf.addPage();
                                    yOffset = margin;
                                }

                                pdf.addImage(imgData, 'JPEG', margin, yOffset, imgWidth, imgHeight);
                                yOffset += imgHeight + 5;
                            }
                        } catch (imgError) {
                            console.warn('Cannot add image to PDF:', imgError);
                            const placeholderData = await addTextAsImage('[Hình ảnh]', 11, false, 0, 0, maxWidth);
                            pdf.addImage(placeholderData.imgData, 'PNG', margin, yOffset, placeholderData.imgWidth, placeholderData.imgHeight);
                            yOffset += placeholderData.imgHeight + 3;
                        }
                    }
                }

                // Separator
                yOffset += 5;
                pdf.setDrawColor(200, 200, 200);
                pdf.line(margin, yOffset, pageWidth - margin, yOffset);
                yOffset += 10;
            }

            // Save PDF
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            pdf.save(`chat-history-${timestamp}.pdf`);

            if (onProgress) onProgress('Hoàn thành!');
            return true;

        } catch (error) {
            console.error('Error creating PDF:', error);
            alert('❌ Lỗi khi tạo PDF: ' + error.message);
            return false;
        } finally {
            this.isExporting = false;
        }
    }

    /**
     * Download chat as JSON
     */
    downloadChatAsJSON(chatHistory) {
        const dataStr = JSON.stringify(chatHistory, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `chat-history-${Date.now()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Download chat as plain text
     */
    downloadChatAsText(chatContainer) {
        const messages = Array.from(chatContainer.children);
        let text = 'AI CHATBOT - LỊCH SỬ HỘI THOẠI\n';
        text += '=' .repeat(50) + '\n\n';
        text += 'Xuất lúc: ' + new Date().toLocaleString('vi-VN') + '\n\n';
        text += '=' .repeat(50) + '\n\n';

        messages.forEach(msg => {
            const isUser = msg.classList.contains('user');
            const textEl = msg.querySelector('.message-text');
            
            if (textEl) {
                const content = textEl.textContent || '';
                text += `${isUser ? '[USER]' : '[AI]'}\n${content}\n\n`;
                text += '-'.repeat(50) + '\n\n';
            }
        });

        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `chat-history-${Date.now()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}
