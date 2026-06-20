import re
import time
import requests
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="Consulta CNPJ")

ultima_requisicao = 0
INTERVALO = 21


def fmt(val, fallback="N/I"):
    if val is None:
        return fallback
    if isinstance(val, str) and val.strip() == "":
        return fallback
    return str(val).strip()


def fmt_moeda(val):
    if not val:
        return "N/I"
    try:
        num = float(str(val).replace(",", "."))
        return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(val)


def fmt_cnpj(val):
    if not val:
        return "N/I"
    n = re.sub(r"\D", "", str(val))
    if len(n) == 14:
        return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"
    return val


def fmt_telefone(ddd, numero):
    if not numero:
        return None
    tel = re.sub(r"\D", "", str(numero))
    d = re.sub(r"\D", "", str(ddd)) if ddd else ""
    if d:
        if len(tel) == 8:
            return f"({d}) {tel[:4]}-{tel[4:]}"
        elif len(tel) == 9:
            return f"({d}) {tel[:5]}-{tel[5:]}"
        else:
            return f"({d}) {tel}"
    else:
        if len(tel) == 8:
            return f"{tel[:4]}-{tel[4:]}"
        elif len(tel) == 9:
            return f"{tel[:5]}-{tel[5:]}"
        return tel


def fmt_cep(val):
    if not val:
        return "N/I"
    n = re.sub(r"\D", "", str(val))
    if len(n) == 8:
        return f"{n[:5]}-{n[5:]}"
    return val


PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Consulta CNPJ</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0f0f1a; color: #e0e0e0; min-height: 100vh;
    display: flex; justify-content: center; padding: 40px 16px;
  }}
  .container {{ max-width: 720px; width: 100%; }}
  h1 {{ text-align: center; font-size: 2rem; color: #2ecc71; margin-bottom: 4px; }}
  .sub {{ text-align: center; color: #666680; margin-bottom: 24px; font-size: 0.9rem; }}
  .card {{
    background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 16px;
    border: 1px solid #2a2a3e;
  }}
  .row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .field {{ flex: 1; min-width: 180px; }}
  .field label {{ display: block; font-size: 0.8rem; color: #888899; margin-bottom: 4px; }}
  .field input {{
    width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid #333;
    background: #0f0f1a; color: #fff; font-size: 1rem; outline: none; transition: border .2s;
  }}
  .field input:focus {{ border-color: #2ecc71; }}
  .field input::placeholder {{ color: #555; }}
  button {{
    background: #2ecc71; color: #000; font-weight: 700; font-size: 1rem;
    border: none; border-radius: 8px; padding: 10px 28px; cursor: pointer;
    transition: background .2s; white-space: nowrap; height: 42px; align-self: flex-end;
  }}
  button:hover {{ background: #27ae60; }}
  button:disabled {{ background: #555; cursor: not-allowed; }}
  .btn-wrap {{ display: flex; align-items: flex-end; gap: 8px; }}
  .spinner {{ display: none; font-size: 1.4rem; color: #2ecc71; margin-bottom: 4px; }}
  .spinner.on {{ display: inline-block; }}
  #aviso {{ color: #e74c3c; font-size: 0.85rem; margin-top: 8px; min-height: 1.2em; }}
  .secao {{
    background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 12px;
    border: 1px solid #2a2a3e; display: none;
  }}
  .secao.visible {{ display: block; }}
  .secao h2 {{ font-size: 1rem; color: #2ecc71; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #2a2a3e; }}
  .linha {{ display: flex; padding: 3px 0; gap: 8px; font-size: 0.9rem; }}
  .rotulo {{ color: #888899; min-width: 180px; flex-shrink: 0; }}
  .valor {{ color: #f0f0f0; word-break: break-word; }}
  .valor.destaque {{ color: #2ecc71; font-weight: 700; }}
  .valor.erro {{ color: #e74c3c; }}
  .erro-box {{
    background: #1e1e2e; border: 1px solid #e74c3c; border-radius: 12px;
    padding: 24px; text-align: center; color: #e74c3c; display: none; margin-bottom: 12px;
  }}
  .erro-box.visible {{ display: block; }}
  @media (max-width: 600px) {{
    body {{ padding: 20px 12px; }}
    .linha {{ flex-direction: column; padding: 4px 0; }}
    .rotulo {{ min-width: auto; }}
  }}
  @@keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
  .spinner-icon {{ display: inline-block; animation: spin .8s linear infinite; }}
</style>
</head>
<body>
<div class="container">
  <h1>Consulta CNPJ</h1>
  <p class="sub">Consulte dados completos de empresas brasileiras</p>

  <div class="card">
    <div class="row">
      <div class="field">
        <label for="cnpj">CNPJ</label>
        <input id="cnpj" placeholder="00.000.000/0001-91" maxlength="18">
      </div>
      <div class="field" style="min-width:80px;max-width:120px">
        <label for="uf">UF</label>
        <input id="uf" placeholder="SP" maxlength="2" value="SP">
      </div>
      <div class="btn-wrap">
        <button id="btn">Consultar</button>
        <span id="spinner" class="spinner"><span class="spinner-icon">&#9696;</span></span>
      </div>
    </div>
    <div id="aviso"></div>
  </div>

  <div id="erroBox" class="erro-box"></div>
  <div id="resultados"></div>
</div>

<script>
const cnpjInp = document.getElementById('cnpj');
const ufInp = document.getElementById('uf');
const btn = document.getElementById('btn');
const spinner = document.getElementById('spinner');
const aviso = document.getElementById('aviso');
const erroBox = document.getElementById('erroBox');
const resultados = document.getElementById('resultados');

cnpjInp.addEventListener('input', function() {{
  let v = this.value.replace(/\\D/g, '').slice(0,14);
  let m = '';
  if (v.length > 0) m += v.slice(0,2);
  if (v.length > 2) m += '.' + v.slice(2,5);
  if (v.length > 5) m += '.' + v.slice(5,8);
  if (v.length > 8) m += '/' + v.slice(8,12);
  if (v.length > 12) m += '-' + v.slice(12);
  let pos = this.selectionStart;
  let diff = m.length - this.value.length;
  if (m !== this.value) {{
    this.value = m;
    this.setSelectionRange(pos + diff, pos + diff);
  }}
}});

btn.addEventListener('click', consultar);
ufInp.addEventListener('keydown', e => {{ if (e.key === 'Enter') consultar(); }});
cnpjInp.addEventListener('keydown', e => {{ if (e.key === 'Enter') consultar(); }});

async function consultar() {{
  const cnpj = cnpjInp.value.replace(/\\D/g, '');
  const uf = ufInp.value.trim().toUpperCase();
  aviso.textContent = '';
  erroBox.classList.remove('visible');
  erroBox.textContent = '';

  if (cnpj.length !== 14) {{ aviso.textContent = 'CNPJ inválido. Deve ter 14 dígitos.'; return; }}
  if (!uf || uf.length !== 2) {{ aviso.textContent = 'UF inválida.'; return; }}

  btn.disabled = true;
  btn.textContent = 'Consultando...';
  spinner.classList.add('on');
  resultados.innerHTML = '';

  try {{
    const r = await fetch(`/api/consultar?cnpj=${{cnpj}}&uf=${{uf}}`);
    const data = await r.json();
    if (data.erro) {{
      erroBox.textContent = data.erro;
      erroBox.classList.add('visible');
      return;
    }}
    renderResultados(data);
  }} catch(e) {{
    erroBox.textContent = 'Erro de conexão com o servidor.';
    erroBox.classList.add('visible');
  }} finally {{
    btn.disabled = false;
    btn.textContent = 'Consultar';
    spinner.classList.remove('on');
  }}
}}

function secao(titulo, linhas) {{
  let h = `<div class="secao visible"><h2>${{titulo}}</h2>`;
  for (const l of linhas) {{
    if (!l) continue;
    let cls = 'valor';
    if (l.destaque) cls += ' destaque';
    if (l.erro) cls += ' erro';
    h += `<div class="linha"><span class="rotulo">${{l.r || ''}}</span><span class="${{cls}}">${{l.v || ''}}</span></div>`;
  }}
  h += '</div>';
  return h;
}}

function s(r, v, opts) {{ return opts ? {{ r, v, ...opts }} : {{ r, v }}; }}

function renderResultados(d) {{
  const e = d.estabelecimento || {{}};
  let html = '';

  html += secao('Dados da Empresa', [
    s('CNPJ', fmtCnpj(e.cnpj), {{destaque:true}}),
    s('Razão Social', d.razao_social, {{destaque:true}}),
    s('Nome Fantasia', e.nome_fantasia || 'N/I'),
    s('Tipo', e.tipo),
    s('Porte', (d.porte||{{}}).descricao),
    s('Natureza Jurídica', (d.natureza_juridica||{{}}).descricao),
    s('Capital Social', fmtMoeda(d.capital_social), {{destaque:true}}),
    s('Responsável Federativo', d.responsavel_federativo),
    s('Qualificação', (d.qualificacao_do_responsavel||{{}}).descricao),
    s('Início Atividade', e.data_inicio_atividade),
  ]);

  const sit = (e.situacao_cadastral || '').toUpperCase();
  html += secao('Situação Cadastral', [
    s('Situação', e.situacao_cadastral, {{destaque: sit==='ATIVA'||sit==='ATIVO', erro: sit!=='ATIVA'&&sit!=='ATIVO'&&sit!==''}}),
    s('Data Situação', e.data_situacao_cadastral),
    e.situacao_especial ? s('Situação Especial', e.situacao_especial) : null,
    e.data_situacao_especial ? s('Data Situação Esp.', e.data_situacao_especial) : null,
    e.motivo_situacao_cadastral ? s('Motivo', e.motivo_situacao_cadastral) : null,
  ]);

  const sim = d.simples;
  if (sim) {{
    html += secao('Simples Nacional / MEI', [
      s('Optante Simples', sim.simples ? 'Sim' : 'Não', {{destaque: sim.simples, erro: !sim.simples}}),
      sim.data_opcao_simples ? s('Data Opção', sim.data_opcao_simples) : null,
      sim.data_exclusao_simples ? s('Data Exclusão', sim.data_exclusao_simples, {{erro:true}}) : null,
      s('Optante MEI', sim.mei ? 'Sim' : 'Não', {{destaque: sim.mei, erro: !sim.mei}}),
      sim.data_opcao_mei ? s('Data Opção MEI', sim.data_opcao_mei) : null,
      sim.data_exclusao_mei ? s('Data Exclusão MEI', sim.data_exclusao_mei, {{erro:true}}) : null,
    ]);
  }}

  const lograd = `${{e.tipo_logradouro || ''}} ${{e.logradouro || ''}}`.trim();
  const num = e.numero || 'N/I';
  const compl = e.complemento || '';
  const cid = typeof e.cidade === 'object' ? (e.cidade.nome || '') : (e.cidade || '');
  const est = typeof e.estado === 'object' ? (e.estado.sigla || '') : (e.estado || '');
  let end = `${{lograd}}, ${{num}}`;
  if (compl) end += ` - ${{compl}}`;

  html += secao('Endereço', [
    s('Logradouro', end, {{destaque:true}}),
    s('Bairro', e.bairro),
    s('Município', `${{cid}} / ${{est}}`),
    s('CEP', fmtCep(e.cep)),
  ]);

  let tels = [];
  if (e.ddd1 && e.telefone1) tels.push(fmtTel(e.ddd1, e.telefone1));
  if (e.ddd2 && e.telefone2) tels.push(fmtTel(e.ddd2, e.telefone2));
  if (e.ddd_fax && e.fax) tels.push('Fax: ' + fmtTel(e.ddd_fax, e.fax));
  if (!tels.length) tels.push('Nenhum telefone encontrado');

  html += secao('Contato', [
    s('Email', e.email || 'Nenhum email encontrado'),
    ...tels.map((t, i) => s(i === 0 ? 'Telefone' : '', t, {{destaque: i === 0}})),
  ]);

  const atvP = e.atividade_principal || {{}};
  const atvs = e.atividades_secundarias || [];
  let atvLines = [s('CNAE Principal', `${{atvP.id || ''}} - ${{atvP.descricao || ''}}`, {{destaque:true}})];
  atvs.slice(0,5).forEach((a, i) => {{
    atvLines.push(s(i === 0 ? 'Secundárias' : '', `${{a.id}} - ${{a.descricao}}`));
  }});
  if (atvs.length > 5) atvLines.push(s('', `... e mais ${{atvs.length - 5}} atividade(s)`));
  html += secao('Atividades', atvLines);

  const ies = e.inscricoes_estaduais || [];
  let ieLines = [];
  if (!ies.length) {{
    ieLines.push(s('', 'Nenhuma inscrição estadual encontrada'));
  }} else {{
    let achou = false;
    ies.forEach(ie => {{
      const sig = ie.estado.sigla;
      const at = ie.ativo;
      const ok = sig === d.uf;
      if (ok) achou = true;
      ieLines.push(s(ok ? `>> ${{sig}}` : `  ${{sig}}`, `${{ie.inscricao_estadual}} (${{at ? 'Ativo' : 'Inativo'}})`, {{destaque: ok, erro: !at && !ok}}));
    }});
    if (!achou) ieLines.push(s(`  ${{d.uf}}`, 'Não encontrada', {{erro:true}}));
  }}
  html += secao('Inscrições Estaduais', ieLines);

  const socios = d.socios || [];
  if (socios.length) {{
    let socLines = [];
    socios.forEach((soc, i) => {{
      const q = typeof soc.qualificacao_socio === 'object' ? soc.qualificacao_socio.descricao : '';
      let txt = soc.nome;
      if (soc.tipo) txt += ` (${{soc.tipo}})`;
      socLines.push(s(`Sócio ${{i+1}}`, txt, {{destaque: i === 0}}));
      if (q) socLines.push(s('', q));
      if (soc.data_entrada) socLines.push(s('', `Desde: ${{soc.data_entrada}}`));
    }});
    html += secao(`Sócios (${{socios.length}})`, socLines);
  }}

  html += secao('Informações Adicionais', [
    s('CNPJ Raiz', d.cnpj_raiz),
    s('Atualizado em', d.atualizado_em),
    e.pais && typeof e.pais === 'object' ? s('País', e.pais.nome) : null,
    e.cnpj_ordem && e.cnpj_digito_verificador ? s('Ordem/DV', `${{e.cnpj_ordem}}/${{e.cnpj_digito_verificador}}`) : null,
  ]);

  resultados.innerHTML = html;
}}

function fmtCnpj(v) {{
  if (!v) return 'N/I';
  const n = v.replace(/\\D/g, '');
  if (n.length === 14) return `${{n.slice(0,2)}}.${{n.slice(2,5)}}.${{n.slice(5,8)}}/${{n.slice(8,12)}}-${{n.slice(12)}}`;
  return v;
}}
function fmtMoeda(v) {{
  if (!v) return 'N/I';
  const n = parseFloat(String(v).replace(',','.'));
  if (isNaN(n)) return v;
  return 'R$ ' + n.toLocaleString('pt-BR', {{minimumFractionDigits:2, maximumFractionDigits:2}});
}}
function fmtTel(ddd, num) {{
  if (!num) return '';
  let t = num.replace(/\\D/g,'');
  let d = ddd ? String(ddd).replace(/\\D/g,'') : '';
  if (d) {{
    if (t.length===8) return `(${{d}}) ${{t.slice(0,4)}}-${{t.slice(4)}}`;
    if (t.length===9) return `(${{d}}) ${{t.slice(0,5)}}-${{t.slice(5)}}`;
    return `(${{d}}) ${{t}}`;
  }}
  if (t.length===8) return `${{t.slice(0,4)}}-${{t.slice(4)}}`;
  if (t.length===9) return `${{t.slice(0,5)}}-${{t.slice(5)}}`;
  return t;
}}
function fmtCep(v) {{
  if (!v) return 'N/I';
  const n = v.replace(/\\D/g, '');
  if (n.length === 8) return `${{n.slice(0,5)}}-${{n.slice(5)}}`;
  return v;
}}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGINA


@app.get("/api/consultar")
def consultar(cnpj: str = Query(...), uf: str = Query(...)):
    global ultima_requisicao

    cnpj_limpo = re.sub(r"\D", "", cnpj)
    uf = uf.strip().upper()

    if len(cnpj_limpo) != 14:
        return {"erro": "CNPJ inválido. Deve ter 14 dígitos."}
    if not uf or len(uf) != 2:
        return {"erro": "UF inválida."}

    agora = time.time()
    desde = agora - ultima_requisicao
    if desde < INTERVALO:
        espera = int(INTERVALO - desde)
        return {"erro": f"Aguardando {espera}s (limite de 3 req/min). Tente novamente."}

    url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    try:
        resp = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        return {"erro": "Tempo limite excedido."}
    except requests.exceptions.ConnectionError:
        return {"erro": "Erro de conexão."}
    except Exception as e:
        return {"erro": f"Erro: {e}"}

    ultima_requisicao = time.time()

    if resp.status_code == 429:
        return {"erro": "Limite de requisições excedido no CNPJ.ws. Aguarde 1 minuto."}
    if resp.status_code != 200:
        return {"erro": f"Erro {resp.status_code} ao consultar API."}

    data = resp.json()
    data["uf"] = uf
    return data
