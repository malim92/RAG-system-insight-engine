package com.insightengine.service;

import com.insightengine.model.Document;
import com.insightengine.model.DocumentStatus;
import com.insightengine.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final RedisQueueService redisQueueService;

    @Value("${app.upload.dir:uploads}")
    private String uploadDir;

    public Document uploadDocument(MultipartFile file, String tenantId) throws IOException {
        // Ensure upload directory exists
        Path uploadPath = Paths.get(uploadDir).toAbsolutePath().normalize();
        Files.createDirectories(uploadPath);

        // Generate safe filename
        String originalName = file.getOriginalFilename();
        String storedName = UUID.randomUUID() + "_" + sanitizeFilename(originalName);
        Path targetPath = uploadPath.resolve(storedName);

        // Save file to disk
        Files.copy(file.getInputStream(), targetPath, StandardCopyOption.REPLACE_EXISTING);
        log.info("Saved file to: {}", targetPath);

        // Save metadata to database
        Document document = Document.builder()
                .originalName(originalName)
                .storedPath(targetPath.toString())
                .contentType(file.getContentType())
                .status(DocumentStatus.PENDING)
                .tenantId(tenantId != null ? tenantId : "default")
                .build();

                try {
                    
                    Document saved = documentRepository.save(document);
                    log.info("Document saved with id: {}", saved.getId());
                    // Enqueue for processing
                    Map<String, Object> job = Map.of(
                            "documentId", saved.getId().toString(),
                            "storedPath", targetPath.toString(),
                            "originalName", originalName,
                            "tenantId", saved.getTenantId()
                    );
                    redisQueueService.enqueueDocumentJob(job);
            
                    return saved;
                } catch (Exception e) {
                   throw new IOException("Failed to save document metadata: " + e.getMessage(), e);
                }

    }

    public Optional<Document> getDocument(UUID documentId) {
        return documentRepository.findById(documentId);
    }

    public List<Document> getAllDocuments() {
        List<Document> documents = documentRepository.findAll();
        if (documents.isEmpty()) {
            throw new RuntimeException("No documents found");
        }

        return documents;
    }

    public Document updateStatus(UUID documentId, DocumentStatus status, String errorMessage) {
        Document document = documentRepository.findById(documentId)
                .orElseThrow(() -> new RuntimeException("Document not found: " + documentId));
        document.setStatus(status);
        document.setErrorMessage(errorMessage);
        return documentRepository.save(document);
    }

    private String sanitizeFilename(String filename) {
        if (filename == null) return "unknown";
        return filename.replaceAll("[^a-zA-Z0-9.\\-]", "_");
    }
}
