"""Generate Word2JATS demonstration manuscripts covering current MVP features."""

import struct
import zlib
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "sample_documents"
MAIN_OUTPUT = OUTPUT_DIR / "word2jats_feature_acceptance.docx"
EDGE_OUTPUT = OUTPUT_DIR / "word2jats_image_edge_cases.docx"


def make_png(path: Path, color: tuple[int, int, int], label_band: int) -> None:
    width, height = 520, 190
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            in_card = 30 < x < 490 and 30 < y < 160
            in_band = 55 + label_band * 20 < x < 215 + label_band * 20 and 70 < y < 120
            pixel = color if in_card else (243, 240, 230)
            if in_band:
                pixel = (255, 255, 255)
            row.extend((*pixel, 255))
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def add_title(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(18)


def add_picture(document: Document, filename: str, color: tuple[int, int, int], band: int) -> None:
    image_path = OUTPUT_DIR / filename
    make_png(image_path, color, band)
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(image_path), width=Inches(5.3))
    image_path.unlink()


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)


def build_main_document() -> Document:
    document = Document()
    configure_document(document)
    add_title(document, "Word2JATS：学术期刊 Word 智能结构化转换功能验收稿")

    document.add_paragraph("张三，李四，王五")
    document.add_paragraph("未来出版大学 数字出版学院，智能内容处理实验室")
    document.add_paragraph(
        "摘要：本文构造一份覆盖 Word2JATS 当前能力的学术期刊测试稿件，"
        "用于验证从 Word 文档到结构化 JSON 和 JATS XML 的完整转换流程。"
    )
    document.add_paragraph(
        "测试内容包括元数据、多级章节、列表、公式、图片、不同格式图题、"
        "参考文献、基础校验及人工校正后重新生成 XML。"
    )
    document.add_paragraph("关键词：JATS；Word；结构化出版；XML；人工校正")

    document.add_paragraph("1 引言")
    document.add_paragraph(
        "学术期刊需要将作者提交的 Word 稿件转换为机器可读、可交换和可长期保存的结构化内容。"
    )

    document.add_paragraph("1.1 研究背景")
    document.add_paragraph(
        "传统人工标引流程成本较高，规则驱动方法可以提供透明、可复核的自动化转换起点。"
    )

    document.add_paragraph("二、系统方法")
    document.add_paragraph("系统采用无状态转换流水线，并依次执行以下步骤：")
    document.add_paragraph("（1）解析 Word 段落、样式与文档媒体")
    document.add_paragraph("（2）构建统一的 article JSON")
    document.add_paragraph("（3）生成并校验 JATS XML")

    add_picture(document, "architecture.png", (0, 109, 119), 0)
    document.add_paragraph("图1 Word2JATS 系统总体架构")
    add_picture(document, "workflow.png", (199, 138, 30), 1)
    document.add_paragraph("图 2 实验流程")
    add_picture(document, "modules.png", (52, 92, 128), 2)
    document.add_paragraph("图1-1 核心模块关系")
    add_picture(document, "overview.png", (78, 126, 92), 3)
    document.add_paragraph("Fig. 4 Overview")
    document.add_paragraph("Figure 5 Caption-only architecture description")

    document.add_paragraph("（一）公式识别")
    document.add_paragraph("F = α × precision + β × recall")
    document.add_paragraph("x ≈ μ + σ")
    document.add_paragraph("∑ x_i ≤ λ")
    document.add_paragraph("∫ f(x) dx ≥ 0")
    document.add_paragraph(r"\frac{a}{b} = \sqrt{c}")
    document.add_paragraph("lim x→0 sin(x) / x = 1")
    document.add_paragraph("log(a) + cos(β) = γ")
    document.add_paragraph("其中各参数用于测试基础规则公式识别。")

    document.add_paragraph("3 结果与讨论")
    document.add_paragraph(
        "转换完成后，用户可以查看 JSON 和 XML，在人工校正页面修改结构数据，"
        "并根据修改后的 article JSON 重新生成 XML。"
    )

    document.add_paragraph("3.1 校验结果")
    document.add_paragraph(
        "系统检查标题、摘要、关键词、章节、XML 合法性和 JATS 核心节点，"
        "并提示 ORCID、单位、图题、公式、空章节及参考文献等出版质量问题。"
    )

    document.add_paragraph("4 结论")
    document.add_paragraph(
        "该验收稿件能够覆盖 Word2JATS 当前已实现的主要转换、校正和校验功能。"
    )

    document.add_paragraph("参考文献")
    document.add_paragraph("[1] 张三, 李四. 学术出版结构化技术研究[J]. 数字出版, 2025, 10(2): 1-8.")
    document.add_paragraph("2. National Information Standards Organization. JATS: Journal Article Tag Suite[S].")
    document.add_paragraph("（3）王五. Word 文档智能解析方法研究[J]. 出版科学, 2026, 34(1): 20-28.")
    return document


def build_image_edge_document() -> Document:
    document = Document()
    configure_document(document)
    add_title(document, "Word2JATS 图片多于图题边界测试")
    document.add_paragraph("测试作者")
    document.add_paragraph("未来出版大学")
    document.add_paragraph("摘要：该文档用于验证图片数量多于图题数量时的宽容绑定策略。")
    document.add_paragraph("关键词：图片；图题；边界测试")
    document.add_paragraph("1 图片测试")
    document.add_paragraph("下方包含三张图片，但仅提供两个图题。")
    add_picture(document, "edge_1.png", (0, 109, 119), 0)
    add_picture(document, "edge_2.png", (199, 138, 30), 1)
    add_picture(document, "edge_3.png", (52, 92, 128), 2)
    document.add_paragraph("图1 第一张图片")
    document.add_paragraph("Figure 2 Second image")
    document.add_paragraph("References")
    document.add_paragraph("[1] 图片边界测试参考文献.")
    return document


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_main_document().save(MAIN_OUTPUT)
    build_image_edge_document().save(EDGE_OUTPUT)
    print(MAIN_OUTPUT)
    print(EDGE_OUTPUT)
