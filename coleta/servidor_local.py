"""Servidor só para teste na rede local. Manda 'no-cache' em tudo para o navegador
sempre pegar a versão nova do site e dos dados. Em produção quem serve é o Cloudflare.

Uso: python3 servidor_local.py --pasta ../site --porta 8470
"""
import argparse
import functools
import hashlib
import os
import http.server


class SemCache(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        """Como o TSE/CDN: ETag pelo conteúdo e 304 quando o If-None-Match bate."""
        caminho = self.translate_path(self.path)
        if os.path.isfile(caminho):
            try:
                etag = '"' + hashlib.md5(open(caminho, "rb").read()).hexdigest() + '"'
            except OSError:
                etag = None
            if etag and self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return None
            self._etag = etag
        return super().send_head()

    def end_headers(self):
        if getattr(self, "_etag", None):
            self.send_header("ETag", self._etag)
            self._etag = None
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--porta", type=int, default=8470)
    a = ap.parse_args()
    h = functools.partial(SemCache, directory=a.pasta)
    http.server.ThreadingHTTPServer(("0.0.0.0", a.porta), h).serve_forever()
