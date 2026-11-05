"use strict";
// Pure sorting checks for the Android WebView bundle; no emulator or dependencies needed.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.resolve(__dirname, "../app/src/main/assets/index.html"), "utf8");
const markup = html.split("<script>")[0];
const js = html.split("<script>")[1].split("</script>")[0];
assert.equal((markup.match(/id="sortReverse"/g) || []).length, 1, "Exactly one reverse button");
assert.match(markup, /class="sort-reverse"/);
assert.match(markup, /aria-pressed="false"/);
assert.doesNotMatch(markup, /alphabetRail|alphabet-letter|jumpToLetter/, "No desktop A-Z navigation");
assert.match(js, /wrld-android-sort-reversed/);
assert.match(js, /saveSortDirection\(\);render\(\)/);
assert.match(js, /function songsForView\(\)/);
assert.match(js, /Preserve chronological history and hand-curated playlist order/);

// Evaluate the actual comparator extracted from the shipped WebView source.
const start = js.indexOf("function compare(a,b){");
const end = js.indexOf("const reduceMotion=", start);
assert.ok(start >= 0 && end > start, "Android comparator must exist");
const state = {sort: "title", sortReversed: false};
const comparator = new Function("app", js.slice(start, end) + "\nreturn compare;")(state);
const songs = [
 {title: "Track 10",artist:"Zebra",duration:0,modified:10},
 {title: "Track 2",artist:"Alpha",duration:180000,modified:30},
 {title: "Track 1",artist:"Alpha",duration:240000,modified:20}
];
const titles = () => [...songs].sort(comparator).map(x => x.title);
assert.deepEqual(titles(), ["Track 1", "Track 2", "Track 10"], "Natural title A-Z");
state.sortReversed = true;
assert.deepEqual(titles(), ["Track 10", "Track 2", "Track 1"], "Natural title Z-A");
state.sort = "duration";state.sortReversed = false;
assert.deepEqual(titles(), ["Track 2", "Track 1", "Track 10"], "Shortest first, unknown last");
state.sortReversed = true;
assert.deepEqual(titles(), ["Track 1", "Track 2", "Track 10"], "Longest first, unknown still last");
state.sort = "added";state.sortReversed = false;
assert.deepEqual(titles(), ["Track 2", "Track 1", "Track 10"], "Newest first");
state.sortReversed = true;
assert.deepEqual(titles(), ["Track 10", "Track 1", "Track 2"], "Oldest first");
state.sort = "artist";state.sortReversed = false;
assert.deepEqual(titles(), ["Track 1", "Track 2", "Track 10"], "Artist A-Z with title tie");
state.sortReversed = true;
assert.deepEqual(titles(), ["Track 10", "Track 1", "Track 2"], "Artist Z-A with title tie");
console.log("Android reverse sorting passed: Title, Length, Date added, Artist, persistence hooks and mobile UI.");
