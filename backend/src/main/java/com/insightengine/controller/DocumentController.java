package com.insightengine.controller;

import com.insightengine.model.Document;
import com.insightengine.model.DocumentStatus;
import com.insightengine.service.DocumentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping("/upload")
    public ResponseEntity<?> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestHeader(value = "X-Tenant-Id", required = false) String tenantId) {

        log.info("Upload request: file={}, size={}, tenant={}",
                file.getOriginalFilename(), file.getSize(), tenantId);

        try {
            if (file.isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("error", "File is empty"));
            }

            Document document = documentService.uploadDocument(file, tenantId);
            log.info("Document uploaded successfully: id={}, status={}", document.getId(), document.getStatus());
            return ResponseEntity.status(HttpStatus.ACCEPTED).body(Map.of(
                    "documentId", document.getId().toString(),
                    "status", document.getStatus().toString(),
                    "originalName", document.getOriginalName()
            ));
        } catch (IOException e) {
            log.error("Upload failed", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Upload failed: " + e.getMessage()));
        }
    }

    /**
     * Callback endpoint called by the Python AI service after processing.
     */
    @PostMapping("/{documentId}/status")
    public ResponseEntity<?> updateStatus(
            @PathVariable UUID documentId,
            @RequestBody Map<String, String> body) {

        String statusStr = body.get("status");
        String errorMessage = body.get("errorMessage");

        try {
            DocumentStatus status = DocumentStatus.valueOf(statusStr.toUpperCase());
            Document document = documentService.updateStatus(documentId, status, errorMessage);
            return ResponseEntity.ok(Map.of(
                    "documentId", document.getId().toString(),
                    "status", document.getStatus().toString()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "Invalid status: " + statusStr));
        }
    }

    @GetMapping("/getDocuments")
    public ResponseEntity<?> getAllDocuments() {
        log.info("Retrieving all documents");
        try {
            List<Document> documents = documentService.getAllDocuments();
            return ResponseEntity.ok(documents);
        } catch (Exception e) {
            log.error("Failed to retrieve documents", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to retrieve documents: " + e.getMessage()));
        }
    }
}
