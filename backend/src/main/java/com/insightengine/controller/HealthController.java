package com.insightengine.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class HealthController {

    private final WebClient aiServiceWebClient;

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        log.info("Health check requested");
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "insight-engine-backend",
                "version", "0.0.1-SNAPSHOT"
        ));
    }

    @GetMapping("/health/ai-service")
    public ResponseEntity<Map<String, Object>> aiServiceHealth() {
        log.info("Checking AI service health via WebClient");
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> aiHealth = aiServiceWebClient.get()
                    .uri("/health")
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            return ResponseEntity.ok(Map.of(
                    "backend", "UP",
                    "aiService", aiHealth != null ? aiHealth : "UNKNOWN"
            ));
        } catch (Exception e) {
            log.error("AI service health check failed", e);
            return ResponseEntity.status(503).body(Map.of(
                    "backend", "UP",
                    "aiService", "DOWN",
                    "error", e.getMessage()
            ));
        }
    }
}
