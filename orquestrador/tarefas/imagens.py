import base64
import binascii
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from orquestrador.celery_aplicacao import aplicacao_celery
from orquestrador.configuracao import obter_configuracoes

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024
LARGURA_MAXIMA_PERMITIDA = 8_000
FORMATOS_PERMITIDOS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _decodificar_imagem(imagem_base64: str) -> bytes:
    conteudo = imagem_base64.split(",", 1)[-1] if "," in imagem_base64 else imagem_base64
    try:
        dados = base64.b64decode(conteudo, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ValueError("imagem_base64 não contém um base64 válido") from erro

    if not dados:
        raise ValueError("A imagem enviada está vazia")
    if len(dados) > TAMANHO_MAXIMO_BYTES:
        raise ValueError("A imagem excede o limite de 10 MB")
    return dados


def _preparar_para_salvar(imagem: Image.Image, formato: str) -> Image.Image:
    if formato == "JPEG" and imagem.mode not in {"RGB", "L"}:
        fundo = Image.new("RGB", imagem.size, "white")
        if imagem.mode == "RGBA":
            fundo.paste(imagem, mask=imagem.getchannel("A"))
        else:
            fundo.paste(imagem.convert("RGB"))
        return fundo
    return imagem


@aplicacao_celery.task(name="tarefas.processar_imagem")
def processar_imagem(
    imagem_base64: str,
    largura_maxima: int,
) -> dict[str, str | int]:
    """Redimensiona uma imagem sem ampliar e salva o resultado em volume Docker."""
    if largura_maxima < 1 or largura_maxima > LARGURA_MAXIMA_PERMITIDA:
        raise ValueError("largura_maxima deve estar entre 1 e 8.000 pixels")

    dados = _decodificar_imagem(imagem_base64)
    try:
        with Image.open(BytesIO(dados)) as verificacao:
            verificacao.verify()
    except (UnidentifiedImageError, OSError) as erro:
        raise ValueError("O conteúdo enviado não é uma imagem válida") from erro

    with Image.open(BytesIO(dados)) as original:
        try:
            formato = original.format or ""
            if formato not in FORMATOS_PERMITIDOS:
                permitidos = ", ".join(sorted(FORMATOS_PERMITIDOS))
                raise ValueError(f"Formato não suportado. Use: {permitidos}")

            largura_original, altura_original = original.size
            if largura_original > largura_maxima:
                proporcao = largura_maxima / largura_original
                dimensoes = (
                    largura_maxima,
                    max(1, round(altura_original * proporcao)),
                )
                processada = original.resize(dimensoes, Image.Resampling.LANCZOS)
            else:
                processada = original.copy()

            extensao = FORMATOS_PERMITIDOS[formato]
            diretorio = Path(obter_configuracoes().diretorio_imagens)
            diretorio.mkdir(parents=True, exist_ok=True)
            caminho = diretorio / f"{uuid4()}.{extensao}"
            processada = _preparar_para_salvar(processada, formato)
            processada.save(caminho, format=formato, optimize=True)
            largura_final, altura_final = processada.size
        except OSError as erro:
            raise RuntimeError("Não foi possível salvar a imagem processada") from erro

    return {
        "caminho": str(caminho),
        "nome_arquivo": caminho.name,
        "formato": formato,
        "largura_original": largura_original,
        "altura_original": altura_original,
        "largura_final": largura_final,
        "altura_final": altura_final,
    }
