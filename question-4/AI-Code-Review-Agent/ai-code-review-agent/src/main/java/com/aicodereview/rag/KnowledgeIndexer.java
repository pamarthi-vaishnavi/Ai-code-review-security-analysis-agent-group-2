package com.aicodereview.rag;

import java.util.List;

import org.springframework.stereotype.Component;

import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.embedding.onnx.bgesmallenv15q.BgeSmallEnV15QuantizedEmbeddingModel;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;

@Component
public class KnowledgeIndexer {

    private final PdfLoader pdfLoader;
    private final TextChunker textChunker;

    private final EmbeddingModel embeddingModel;
    private final InMemoryEmbeddingStore<TextSegment> embeddingStore;

    public KnowledgeIndexer(PdfLoader pdfLoader,
                            TextChunker textChunker) {

        this.pdfLoader = pdfLoader;
        this.textChunker = textChunker;

        this.embeddingModel = new BgeSmallEnV15QuantizedEmbeddingModel();
        this.embeddingStore = new InMemoryEmbeddingStore<>();
    }

    public void buildKnowledgeBase() {

        System.out.println("Loading PDFs...");

        String text = pdfLoader.loadAllPdfs();

        System.out.println("Splitting into chunks...");

        List<String> chunks = textChunker.splitText(text);

        System.out.println("Total Chunks : " + chunks.size());

        for (String chunk : chunks) {

            TextSegment segment = TextSegment.from(chunk);

            Embedding embedding = embeddingModel
                    .embed(segment)
                    .content();

            embeddingStore.add(embedding, segment);
        }

        System.out.println("-----------------------------------");
        System.out.println("Knowledge Base Ready");
        System.out.println("Indexed Chunks : " + chunks.size());
        System.out.println("-----------------------------------");
    }

    public InMemoryEmbeddingStore<TextSegment> getEmbeddingStore() {
        return embeddingStore;
    }

    public EmbeddingModel getEmbeddingModel() {
        return embeddingModel;
    }
}