# Declarative Slide Templates & Layout Specifications

Use these JSON / YAML specification templates with `knt build --spec deck.json` to generate complete presentations automatically.

---

## 1. Complete Multi-Slide Deck Example (`deck.json`)

```json
{
  "theme": "amil-light",
  "slides": [
    {
      "type": "hero",
      "tag": "Product Launch 2026",
      "title": "Autonomous Infrastructure Platform",
      "subtitle": "Next-generation distributed orchestration with zero-overhead execution.",
      "footer": "Confidential • Internal Use Only",
      "notes": "Welcome everyone. Today we are introducing our new distributed execution engine."
    },
    {
      "type": "content",
      "title": "Platform Architecture Overview",
      "subtitle": "Modular, decoupled micro-kernels built on Apple Silicon Metal acceleration.",
      "content": "• Direct GPU pipeline binding with zero IPC latency\n• Automated semantic analysis using local Vision models\n• Real-time synchronization with cloud state\n• Native integration with Keynote, Pages, and Final Cut Pro",
      "notes": "Highlight local on-device inference speed compared to cloud latency."
    },
    {
      "type": "two_column",
      "title": "Legacy Approach vs Modern Architecture",
      "subtitle": "Side-by-side comparative analysis of execution speed and cost.",
      "col1_title": "Legacy Cloud Workflow",
      "col1_content": "❌ 450ms network round-trip latency\n❌ High recurring API subscription costs\n❌ Privacy and data egress liabilities\n❌ Fragile external network dependencies",
      "col2_title": "Local Metal Acceleration",
      "col2_content": "✅ Sub-10ms instantaneous response\n✅ 100% offline local processing on Apple Silicon\n✅ Zero cloud API costs or subscription lock-in\n✅ Complete privacy and data residency compliance",
      "notes": "Emphasize data privacy for enterprise customers."
    },
    {
      "type": "metrics",
      "title": "Performance Benchmarks & Growth",
      "subtitle": "Measured against industry baselines across 10,000 automated runs.",
      "metrics": [
        {
          "value": "4.8x",
          "label": "Throughput Speedup",
          "desc": "Compared to Python standard multiprocessing"
        },
        {
          "value": "99.98%",
          "label": "Execution Reliability",
          "desc": "Zero fatal IPC crashes across 50,000 requests"
        },
        {
          "value": "-85%",
          "label": "Memory Footprint",
          "desc": "Unified memory zero-copy buffer sharing"
        },
        {
          "value": "$0",
          "label": "Cloud Ingress/Egress",
          "desc": "100% on-device local computation"
        }
      ],
      "notes": "Walk through each metric card in order."
    },
    {
      "type": "code",
      "title": "Live CLI Invocation",
      "subtitle": "Simple single-line terminal command for complete deck generation.",
      "language": "bash",
      "code": "# Inspect active presentation structure\nknt info\n\n# Search and replace text across all slides\nknt text replace \"Old Brand\" \"New Brand\"\n\n# Export active presentation to styled PDF and PNG slide images\nknt export --format pdf --output ./presentation.pdf\nknt export --format png --output ./slides/",
      "notes": "Demonstrate live in terminal."
    },
    {
      "type": "table",
      "title": "Enterprise Feature Matrix",
      "subtitle": "Detailed comparison across standard, pro, and enterprise tiers.",
      "headers": ["Feature", "Standard", "Professional", "Enterprise"],
      "rows": [
        ["Apple Silicon Metal GPU", "Included", "Included", "Included"],
        ["Local Vision OCR Engine", "Basic", "Advanced", "Unlimited"],
        ["Custom Brand Theming", "3 Themes", "8 Themes", "Custom Manifest"],
        ["Concurrent Pipelines", "1", "4", "Unlimited"]
      ],
      "notes": "Summarize pricing and licensing options."
    }
  ]
}
```
