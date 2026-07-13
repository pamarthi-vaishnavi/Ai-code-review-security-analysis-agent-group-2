package com.aicodereview.rag;

import com.aicodereview.loader.PdfLoader;
import com.aicodereview.service.EmbeddingService;
import com.aicodereview.service.TextChunkService;
import com.aicodereview.service.VectorStoreService;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class RagIndexer {

    private final PdfLoader pdfLoader;
    private final TextChunkService chunkService;
    private final EmbeddingService embeddingService;
    private final VectorStoreService vectorStoreService;

    public RagIndexer(PdfLoader pdfLoader,
                      TextChunkService chunkService,
                      EmbeddingService embeddingService,
                      VectorStoreService vectorStoreService) {

        this.pdfLoader = pdfLoader;
        this.chunkService = chunkService;
        this.embeddingService = embeddingService;
        this.vectorStoreService = vectorStoreService;
    }

    @PostConstruct
    public void initializeKnowledgeBase() {

        System.out.println("========================================");
        System.out.println("Loading Knowledge Base...");
        System.out.println("========================================");

        List<String> documents = pdfLoader.loadPdfContents();

        System.out.println("PDFs Loaded : " + documents.size());

        List<String> chunks = chunkService.chunkDocuments(documents);

        System.out.println("Chunks Created : " + chunks.size());

        int indexed = 0;

        for (String chunk : chunks) {

            float[] embedding = embeddingService.generateEmbedding(chunk);

            vectorStoreService.addDocument(chunk, embedding);

            indexed++;
            System.out.println("Indexed " + indexed + " / " + chunks.size());
        }

        System.out.println("----------------------------------------");
        System.out.println("Embeddings Generated : " + indexed);
        System.out.println("Vector Store Size    : " + vectorStoreService.size());
        System.out.println("Knowledge Base Ready");
        System.out.println("========================================");
    }
}