<?php
// Scraper multi-estrategia: funciona con Homecenter, Sodimac, Promart, Easy, etc.

class Scraper {
    private string $url;
    private string $html = '';
    private ?DOMDocument $dom = null;
    private ?DOMXPath $xpath = null;

    private string $tienda = '';
    private string $codigo = '';
    private string $descripcion = '';
    private string $unidad = 'Unidad';
    private float $valor = 0.0;

    private const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36";

    public function __construct(string $url) {
        $this->url = $url;
    }

    public function scrape(): array {
        $this->fetch();
        $this->detectarTienda();

        if (empty($this->html)) {
            return $this->resultado();
        }

        libxml_use_internal_errors(true);
        $this->dom = new DOMDocument();
        $this->dom->loadHTML('<meta charset="utf-8">' . $this->html);
        $this->xpath = new DOMXPath($this->dom);

        // Estrategias en orden
        $this->tryJsonLd();
        $this->tryEmbeddedState();
        $this->tryMetaTags();
        $this->tryMicrodata();
        $this->tryHtmlPatterns();
        $this->tryUrlId();
        $this->tryUnitFromName();
        $this->tryStoreApi();

        return $this->resultado();
    }

    private function resultado(): array {
        return [
            'codigo'      => $this->codigo,
            'descripcion' => $this->descripcion,
            'unidad'      => $this->unidad,
            'valor'       => $this->valor,
            'tienda'      => $this->tienda,
            'url'         => $this->url,
        ];
    }

    // ─── Fetch ────────────────────────────────────────────────
    private function fetch(): void {
        $ch = curl_init($this->url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT        => 30,
            CURLOPT_USERAGENT      => self::UA,
            CURLOPT_HTTPHEADER     => [
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: es-419,es;q=0.9',
            ],
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 400 && $body) {
            $this->html = $body;
        }
    }

    // ─── Detectar tienda ──────────────────────────────────────
    private function detectarTienda(): void {
        $u = strtolower($this->url);
        if (str_contains($u, 'homecenter'))  { $this->tienda = 'Homecenter'; }
        elseif (str_contains($u, 'sodimac'))  { $this->tienda = 'Sodimac'; }
        elseif (str_contains($u, 'promart'))   { $this->tienda = 'Promart'; }
        elseif (str_contains($u, 'easy.com'))  { $this->tienda = 'Easy'; }
        elseif (str_contains($u, 'maestro'))   { $this->tienda = 'Maestro'; }
        else { $this->tienda = 'Otra'; }
    }

    // ─── Estrategia 1: JSON-LD Product ────────────────────────
    private function tryJsonLd(): void {
        if (!$this->xpath) return;
        $scripts = $this->xpath->query("//script[@type='application/ld+json']");
        foreach ($scripts as $s) {
            $data = json_decode($s->textContent, true);
            if (!$data) continue;
            if (isset($data['@graph'])) $data = $data['@graph'][0] ?? $data;
            if (isset($data['@type']) && $data['@type'] === 'Product') {
                if (empty($this->codigo) && !empty($data['sku']))
                    $this->codigo = (string)$data['sku'];
                if (empty($this->descripcion) && !empty($data['name']))
                    $this->descripcion = (string)$data['name'];
                if ($this->valor <= 0 && isset($data['offers']['price']))
                    $this->valor = (float)$data['offers']['price'];
            }
        }
    }

    // ─── Estrategia 2: Estado JS embebido ─────────────────────
    private function tryEmbeddedState(): void {
        $patterns = [
            '/window\.__STATE__\s*=\s*({.*?});/s',
            '/window\.__INITIAL_STATE__\s*=\s*({.*?});/s',
            '/window\.__NUXT__\s*=\s*({.*?});/s',
            '/var\s+skuJson[_\d]*\s*=\s*({.*?});/s',
            '/window\.product\s*=\s*({.*?});/s',
        ];
        foreach ($patterns as $pat) {
            if (preg_match($pat, $this->html, $m)) {
                $data = json_decode($m[1], true);
                if ($data) $this->extractFromArray($data);
            }
        }
    }

    private function extractFromArray(array $data, int $depth = 0): void {
        if ($depth > 5) return;
        foreach ($data as $key => $value) {
            $kl = strtolower($key);
            // Código
            if (empty($this->codigo)) {
                if (in_array($kl, ['sku','productid','productreference','idproducto']) && is_scalar($value))
                    $this->codigo = (string)$value;
            }
            // Descripción
            if (empty($this->descripcion)) {
                if (in_array($kl, ['name','productname','displayname','title']) && is_string($value))
                    $this->descripcion = $value;
            }
            // Valor (detectar centavos)
            if ($this->valor <= 0) {
                if (str_contains($kl, 'price') && is_numeric($value) && $value > 0) {
                    $this->valor = (float)$value;
                }
                if (str_contains($kl, 'fullsellingprice') && is_string($value)) {
                    $nums = [];
                    if (preg_match('/[\d.,]+/', $value, $nums)) {
                        $pv = (float)str_replace(',', '.', $nums[0]);
                        if ($pv > 0 && ($this->valor > $pv * 10 || $this->valor <= 0))
                            $this->valor = $pv;
                    }
                }
            }
            // Unidad
            if ($this->unidad === 'Unidad') {
                if ($kl === 'measurementunit' && is_string($value) && $value) $this->unidad = $value;
                if ($kl === 'unitmultiplier' && is_numeric($value)) $this->unidad = (string)$value;
            }
            if (is_array($value)) $this->extractFromArray($value, $depth + 1);
        }
        // Ajuste: si valor > precio formateado * 10, está en centavos
        if ($this->valor > 99999) $this->valor /= 100;
    }

    // ─── Estrategia 3: Meta tags ──────────────────────────────
    private function tryMetaTags(): void {
        if (!$this->xpath) return;
        $metas = $this->xpath->query("//meta");
        foreach ($metas as $meta) {
            $prop = strtolower($meta->getAttribute('property') ?: $meta->getAttribute('name'));
            $content = $meta->getAttribute('content');
            if (!$content) continue;
            if (empty($this->descripcion) && in_array($prop, ['og:title','twitter:title']))
                $this->descripcion = $content;
            if (empty($this->codigo) && $prop === 'product:retailer_item_id')
                $this->codigo = $content;
            if ($this->valor <= 0 && $prop === 'product:price:amount')
                $this->valor = (float)$content;
        }
    }

    // ─── Estrategia 4: Microdata ──────────────────────────────
    private function tryMicrodata(): void {
        if (!$this->xpath) return;
        if (empty($this->descripcion)) {
            $el = $this->xpath->query("//*[@itemprop='name']")->item(0);
            if ($el) $this->descripcion = trim($el->textContent);
        }
        if (empty($this->codigo)) {
            $el = $this->xpath->query("//*[@itemprop='sku']")->item(0);
            if ($el) $this->codigo = $el->getAttribute('content') ?: trim($el->textContent);
        }
        if ($this->valor <= 0) {
            $el = $this->xpath->query("//*[@itemprop='price']")->item(0);
            if ($el) {
                $c = $el->getAttribute('content') ?: trim($el->textContent);
                $c = preg_replace('/[^\d.,]/', '', $c);
                $c = str_replace(',', '.', $c);
                if (is_numeric($c)) $this->valor = (float)$c;
            }
        }
    }

    // ─── Estrategia 5: HTML patterns ──────────────────────────
    private function tryHtmlPatterns(): void {
        if (!$this->xpath) return;
        if (empty($this->descripcion)) {
            $h1 = $this->xpath->query("//h1")->item(0);
            if ($h1) $this->descripcion = trim($h1->textContent);
        }
        if ($this->valor <= 0) {
            $els = $this->xpath->query("//*[contains(@class,'price') or contains(@class,'precio')]");
            foreach ($els as $el) {
                $t = trim($el->textContent);
                $t = preg_replace('/[^\d.,]/', '', $t);
                $t = str_replace(',', '.', $t);
                if (is_numeric($t) && (float)$t > 0) {
                    $this->valor = (float)$t;
                    break;
                }
            }
        }
    }

    // ─── Estrategia 6: ID desde URL ───────────────────────────
    private function tryUrlId(): void {
        if (!empty($this->codigo)) return;
        $patterns = [
            '/\/product\/(\d+)/', '/(\d+)\/p\/?$/', '/(\d+)\/?$/', '/sku[=:](\d+)/',
        ];
        foreach ($patterns as $p) {
            if (preg_match($p, $this->url, $m)) { $this->codigo = $m[1]; return; }
        }
    }

    // ─── Estrategia 7: Unidad desde nombre ────────────────────
    private function tryUnitFromName(): void {
        if ($this->unidad !== 'Unidad' || empty($this->descripcion)) return;
        $patterns = [
            '/\d+[\.,]?\d*\s*(kg|kilogramo)\b/i'  => 'kg',
            '/\d+[\.,]?\d*\s*(g|gramo)\b/i'       => 'g',
            '/\d+[\.,]?\d*\s*(lts?|litros?|l)\b/i'=> 'L',
            '/\d+[\.,]?\d*\s*(ml|mililitro)\b/i'  => 'mL',
            '/\d+[\.,]?\d*\s*(mts?|metros?|m)\b/i'=> 'm',
            '/\d+[\.,]?\d*\s*(cm|cent[íi]metros?)\b/i'=> 'cm',
            '/\d+[\.,]?\d*\s*(m2|m²|metros?\s*cuadrados?)\b/i'=> 'm²',
            '/\d+[\.,]?\d*\s*(gal[oó]n|gal)\b/i'  => 'gal',
            '/\d+[\.,]?\d*\s*(und|unid|pza|pieza)\b/i' => 'Unidad',
        ];
        foreach ($patterns as $pat => $unit) {
            if (preg_match($pat, ' ' . strtolower($this->descripcion) . ' ', $m)) {
                $this->unidad = $unit; return;
            }
        }
    }

    // ─── Estrategia 8: API de la tienda (VTEX / Falabella) ────
    private function tryStoreApi(): void {
        if (!empty($this->codigo) && $this->valor > 0 && !empty($this->descripcion)) return;
        if (empty($this->codigo)) return;

        $sku = $this->codigo;
        $host = parse_url($this->url, PHP_URL_HOST) ?: '';

        if (str_contains($host, 'homecenter')) {
            $this->callVtexApi($host, $sku);
        } elseif (str_contains($host, 'promart')) {
            $this->callVtexApi($host, $sku);
        } elseif (str_contains($host, 'maestro')) {
            $this->callVtexApi($host, $sku);
        } elseif (str_contains($host, 'easy.com')) {
            $this->callVtexApi($host, $sku);
        } elseif (str_contains($host, 'sodimac')) {
            $this->callFalabellaApi($host, $sku);
        }
    }

    private function callVtexApi(string $host, string $sku): void {
        $endpoints = [
            "https://{$host}/api/catalog_system/pub/products/search?fq=skuId:{$sku}",
            "https://{$host}/api/catalog_system/pub/products/search?fq=productId:{$sku}",
        ];
        foreach ($endpoints as $url) {
            $data = $this->fetchJson($url);
            if (!$data) continue;
            $items = isset($data[0]) ? $data : ($data['products'] ?? [$data]);
            foreach ($items as $item) {
                if (empty($item['productName']) && empty($item['name'])) continue;
                if (empty($this->descripcion))
                    $this->descripcion = $item['productName'] ?? $item['name'] ?? $this->descripcion;
                $inner = $item['items'][0] ?? $item;
                $seller = $inner['sellers'][0] ?? $inner;
                $co = $seller['commertialOffer'] ?? [];
                $price = $co['Price'] ?? $co['spotPrice'] ?? $co['price'] ?? 0;
                if ($price > 0 && $this->valor <= 0) $this->valor = (float)$price;
                return;
            }
        }
    }

    private function callFalabellaApi(string $host, string $sku): void {
        $url = "https://www.falabella.com.pe/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={$sku}";
        $data = $this->fetchJson($url);
        if (!$data) return;
        $product = $data['product'] ?? $data;
        if (empty($this->descripcion))
            $this->descripcion = $product['displayName'] ?? $product['name'] ?? $this->descripcion;
        $items = $product['items'][0] ?? $product;
        $seller = $items['sellers'][0] ?? $items;
        $price = $seller['salePrice'] ?? $seller['commertialOffer']['Price'] ?? 0;
        if ($price > 0 && $this->valor <= 0) $this->valor = (float)$price;
    }

    private function fetchJson(string $url): ?array {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 15,
            CURLOPT_USERAGENT      => self::UA,
            CURLOPT_HTTPHEADER     => ['Accept: application/json'],
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code === 200 && $body) {
            $d = json_decode($body, true);
            return is_array($d) ? $d : null;
        }
        return null;
    }
}
