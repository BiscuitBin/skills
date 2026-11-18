// Renders every top-level `mermaid` block in the given Markdown files with the
// pinned Mermaid (package.json overrides) in the pinned chrome-headless-shell,
// and reports each block that does not render as `path:line: message`, where
// line is the opening fence's. Run it as `just check-mermaid`, whose
// environment keeps Puppeteer's browser and its profile inside .tools/.
//
//   just check-mermaid [--labels] <file-or-glob>...
//
// --labels also prints, for each block, the text of every label and message in
// the rendered SVG, so a reader can see a label that a `#`, `;` or quote cut
// short without any error.
//
// Exit status: 0 when every block renders, 1 when any block fails, 2 on a usage
// error or a browser that does not start.
//
// Limits: GitHub does not publish its Mermaid version, so this checks against
// the pinned one. Only fences at the top level are found: a fence inside a
// block quote, or indented four or more spaces under a list item, is skipped.
// An HTML comment is skipped, fence-looking lines included, as GitHub skips
// it. Other HTML blocks, such as a `<pre>` or a `<details>` up to its first
// blank line, are read as Markdown: a fence in one is checked though GitHub
// would not render it, and a fence one leaves open can hide a later block.

import { existsSync, readFileSync, statSync } from 'node:fs';
import { glob } from 'node:fs/promises';
import path from 'node:path';
import { renderMermaid } from '@mermaid-js/mermaid-cli';
import puppeteer from 'puppeteer';

// GitHub renders with securityLevel 'antiscript'. Mermaid's default maxTextSize
// is 50,000 characters, and Mermaid draws a longer diagram as a placeholder
// that says so, without an error, so the length is checked here instead.
const MERMAID_CONFIG = { securityLevel: 'antiscript' };
const MAX_TEXT_SIZE = 50_000;

const OPENER = /^( {0,3})(`{3,}|~{3,})(.*)$/;
const COMMENT_OPENER = /^ {0,3}<!--/;
// A frame of the browser-side stack that Puppeteer appends to Mermaid's message.
const STACK_FRAME = /^\s+at\s|\(https:\/\/mermaid-cli-intercept\.invalid\//;

class UsageError extends Error {}

/**
 * Every top-level fenced block whose info string starts with the word
 * `mermaid`, as CommonMark reads fences: a fence closes only on the same
 * character, at least as long, with nothing after it, so a fence nested in a
 * longer one is content. An unclosed fence runs to the end of the file.
 *
 * An HTML comment that starts a line outside a fence runs through the first
 * line holding `-->`, its own included, and GitHub shows none of it, so a fence
 * there opens nothing. A `<!--` inside a fence is code.
 */
function mermaidBlocks(text) {
  const blocks = [];
  let open = null;
  let comment = false;
  text.split(/\r?\n/).forEach((line, index) => {
    if (open) {
      const close = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(line);
      if (close && close[1][0] === open.char && close[1].length >= open.length) {
        if (open.mermaid) blocks.push(open);
        open = null;
      } else {
        open.lines.push(line.replace(new RegExp(`^ {0,${open.indent}}`), ''));
      }
      return;
    }
    if (comment || COMMENT_OPENER.test(line)) {
      comment = !line.includes('-->');
      return;
    }
    const match = OPENER.exec(line);
    if (!match) return;
    const [, indent, fence, info] = match;
    // A backtick fence's info string cannot hold a backtick; that line is text.
    if (fence[0] === '`' && info.includes('`')) return;
    open = {
      line: index + 1,
      indent: indent.length,
      char: fence[0],
      length: fence.length,
      mermaid: info.trim().split(/\s+/)[0] === 'mermaid',
      lines: []
    };
  });
  if (open?.mermaid) blocks.push(open);
  return blocks.map((block) => ({
    line: block.line,
    definition: block.lines.map((line) => `${line}\n`).join('')
  }));
}

async function markdownFiles(patterns) {
  const files = [];
  for (const pattern of patterns) {
    if (existsSync(pattern) && statSync(pattern).isFile()) {
      files.push(pattern);
      continue;
    }
    const found = [];
    if (/[*?[{]/.test(pattern)) {
      for await (const file of glob(pattern)) found.push(file);
    }
    const matched = found.filter((file) => statSync(file).isFile()).sort();
    if (matched.length === 0) throw new UsageError(`no file matches ${pattern}`);
    files.push(...matched);
  }
  return [...new Set(files)];
}

function mermaidMessage(error) {
  const kept = [];
  for (const line of String(error?.message ?? error).split('\n')) {
    if (STACK_FRAME.test(line)) break;
    kept.push(line);
  }
  return kept.join('\n').trimEnd();
}

async function launch() {
  const cache = path.resolve(process.env.PUPPETEER_CACHE_DIR);
  let browser;
  try {
    // Chrome's sandbox stays on, since the checker renders agent output. Ubuntu
    // 23.10 and later block the unprivileged user namespaces it needs, so there
    // Chrome starts only once that AppArmor restriction is lifted, as CI does
    // for Codex, or the binary has an AppArmor profile (Puppeteer's
    // troubleshooting guide). --no-sandbox would trade the sandbox away.
    //
    // mermaid-cli serves Mermaid and its fonts from node_modules by request
    // interception, which answers before any proxy, and lets every other request
    // through. A label may hold HTML such as an <img>, so every other request
    // goes to a proxy on a closed port, loopback included, and fails.
    browser = await puppeteer.launch({
      headless: 'shell',
      args: ['--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=<-loopback>']
    });
  } catch (error) {
    throw new UsageError(
      `chrome-headless-shell did not start: ${mermaidMessage(error)}\n` +
        'Run `just install-browser`. On Ubuntu 23.10 or later, see the sandbox note in scripts/check-mermaid.mjs.'
    );
  }
  const executable = browser.process()?.spawnfile ?? '';
  if (!executable.startsWith(cache + path.sep)) {
    await browser.close();
    throw new UsageError(`Puppeteer started ${executable}, not the browser in ${cache}.`);
  }
  return browser;
}

/** The text of every label and message in a rendered SVG, in document order. */
async function svgLabels(reader, svg) {
  await reader.setContent(`<!doctype html><body>${svg}</body>`);
  return reader.$$eval('svg text, svg foreignObject', (nodes) =>
    nodes
      .filter((node) => !node.closest('foreignObject') || node.localName === 'foreignObject')
      .map((node) => {
        const named = node.localName === 'text' ? node : node.querySelector('[class]');
        return { kind: named?.classList[0] ?? node.localName, text: node.textContent };
      })
      .filter((label) => label.text.trim() !== '')
  );
}

async function render(browser, definition) {
  if (definition.length > MAX_TEXT_SIZE) {
    const size = definition.length.toLocaleString('en-US');
    return {
      error: `the diagram is ${size} characters, over Mermaid's maxTextSize of 50,000, so it would show only a "Maximum text size in diagram exceeded" placeholder.`
    };
  }
  try {
    const { data } = await renderMermaid(browser, definition, 'svg', {
      mermaidConfig: MERMAID_CONFIG,
      fontEmbed: false
    });
    const svg = new TextDecoder().decode(data);
    // Mermaid's error diagram, the "Syntax error in text" bomb, can render
    // without a rejection: the `error` diagram type draws it.
    if (/^<svg\b[^>]*\baria-roledescription="error"/.test(svg)) {
      return { error: 'Mermaid drew its "Syntax error in text" error diagram.' };
    }
    return { svg };
  } catch (error) {
    return { error: mermaidMessage(error) };
  }
}

function indented(message) {
  return message.replaceAll('\n', '\n    ');
}

function plural(count, noun) {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

async function main(argv) {
  const labels = argv.includes('--labels');
  const patterns = argv.filter((arg) => arg !== '--labels');
  const unknown = patterns.find((arg) => arg.startsWith('-'));
  if (unknown) throw new UsageError(`unknown option ${unknown}`);
  if (patterns.length === 0) {
    throw new UsageError('usage: just check-mermaid [--labels] <file-or-glob>...');
  }
  if (!process.env.PUPPETEER_CACHE_DIR) {
    throw new UsageError(
      'PUPPETEER_CACHE_DIR is not set. Run this as `just check-mermaid`, whose environment keeps the browser in .tools/puppeteer.'
    );
  }
  const files = await markdownFiles(patterns);
  let browser;
  let reader;
  let blocks = 0;
  let failed = 0;
  try {
    for (const file of files) {
      for (const { line, definition } of mermaidBlocks(readFileSync(file, 'utf8'))) {
        blocks++;
        if (!browser && definition.length <= MAX_TEXT_SIZE) browser = await launch();
        const { svg, error } = await render(browser, definition);
        if (error) failed++;
        if (!labels) {
          if (error) console.log(`${file}:${line}: ${indented(error)}`);
          continue;
        }
        if (error) {
          console.log(`${file}:${line}: error: ${indented(error)}`);
          continue;
        }
        console.log(`${file}:${line}: rendered`);
        if (!reader) {
          reader = await browser.newPage();
          await reader.setJavaScriptEnabled(false);
        }
        for (const { kind, text } of await svgLabels(reader, svg)) {
          console.log(`    ${kind}: ${JSON.stringify(text)}`);
        }
      }
    }
  } finally {
    await browser?.close();
  }
  console.log(
    `check-mermaid: ${plural(blocks, 'block')} in ${plural(files.length, 'file')}, ${failed} failed.`
  );
  return failed ? 1 : 0;
}

try {
  process.exitCode = await main(process.argv.slice(2));
} catch (error) {
  if (!(error instanceof UsageError)) throw error;
  console.error(`check-mermaid: ${error.message}`);
  process.exitCode = 2;
}
