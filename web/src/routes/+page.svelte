<script lang="ts">
	import { onMount } from 'svelte';
	import CategoryChart from '$lib/components/CategoryChart.svelte';
	import ConfidenceCharts from '$lib/components/ConfidenceCharts.svelte';
	import Feed from '$lib/components/Feed.svelte';
	import HeadToHead from '$lib/components/HeadToHead.svelte';
	import LatencyChart from '$lib/components/LatencyChart.svelte';
	import Mistakes from '$lib/components/Mistakes.svelte';
	import Pipeline from '$lib/components/Pipeline.svelte';
	import Race from '$lib/components/Race.svelte';
	import { ago, fmtTimes, int, ms, pct, times, usd } from '$lib/format';
	import { live } from '$lib/live.svelte';

	onMount(() => live.start());

	const s = $derived(live.stats);
	const llm = $derived(s?.engines.llm ?? 'the LLM');
	const running = $derived(live.connected && !s?.paused);
	const sure = $derived(s?.jev_coverage.find((p) => p.threshold === 0.9));
	const lastPaper = $derived(live.papers[0]?.created_at);

	let theme = $state<string | null>(null);
	onMount(() => {
		try { theme = localStorage.getItem('theme'); } catch { /* storage blocked */ }
		if (theme) document.documentElement.dataset.theme = theme;
	});
	function toggleTheme() {
		const dark = theme ? theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
		theme = dark ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		try { localStorage.setItem('theme', theme); } catch { /* storage blocked */ }
	}
</script>

<div class="mx-auto max-w-[1180px] px-4 pt-5 pb-16 sm:px-6">
	<!-- Masthead: a running header, like the top line of a preprint. -->
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-rule pb-2.5 text-xs">
		<span class="font-mono font-semibold tracking-tight">arXiv Classifier</span>
		<span class="text-muted">live evaluation · arXiv cs · {new Date().toLocaleDateString('en', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
		<div class="ml-auto flex items-center gap-2">
			<span class="inline-flex items-center gap-2 text-text-2">
				<span class="relative flex size-2">
					{#if running}<span class="absolute inline-flex size-full animate-ping rounded-full bg-good opacity-70"></span>{/if}
					<span class="relative inline-flex size-2 rounded-full {running ? 'bg-good' : s?.paused ? 'bg-warn' : 'bg-muted'}"></span>
				</span>
				{!live.connected ? 'Connecting…' : s?.paused ? 'Judging stopped' : 'Live'}
			</span>
			{#if s}
				<button onclick={() => live.setPaused(!s.paused)}
					class="rounded-full border px-3 py-1 font-medium transition {s.paused ? 'border-text bg-text text-surface' : 'border-border hover:border-muted'}"
					title={s.paused ? 'Poll arXiv and judge new papers again' : 'Stop polling arXiv and judging new papers (stops the API bill)'}>
					{s.paused ? '▶ Resume judging' : '■ Stop judging'}
				</button>
			{/if}
			<button onclick={toggleTheme} class="rounded-full border border-border px-2.5 py-1 hover:border-muted" aria-label="Toggle dark mode">◐</button>
			<a href="/api/docs" target="_blank" class="rounded-full border border-border px-3 py-1 hover:border-muted">API</a>
		</div>
	</div>

	<!-- Title block -->
	<header class="mt-10 mb-8 max-w-[52rem]">
		<h1 class="font-serif text-[clamp(2rem,5vw,3.4rem)] leading-[1.04] font-medium tracking-[-0.02em] text-balance">
			Can a decision model sort arXiv as well as an LLM?
		</h1>
		<p class="mt-4 text-sm text-text-2">
			<span class="inline-flex items-center gap-1.5"><span class="size-2 rounded-full bg-jev"></span><b class="font-semibold text-text">Jev</b> {s?.engines.jev ?? ''} · TypeSafe AI</span>
			<span class="mx-2 text-muted">vs</span>
			<span class="inline-flex items-center gap-1.5"><span class="size-2 rounded-full bg-llm"></span><b class="font-semibold text-text">{s?.engines.llm ?? 'LLM'}</b></span>
			{#if lastPaper}<span class="ml-2 text-muted">· last paper judged {ago(lastPaper, live.now)}</span>{/if}
		</p>

		<!-- The abstract writes itself from the live numbers. -->
		<div class="mt-6 border-l-2 border-rule pl-5">
			<p class="font-serif text-[1.08rem] leading-relaxed text-text-2">
				<span class="mr-1 font-sans text-xs font-bold tracking-[0.08em] text-text uppercase">Abstract</span>
				{#if s?.n}
					We race Jev, a decision model that returns calibrated probabilities over a fixed set of answers, against
					{llm}, a generative model given the same category definitions, on <b class="num font-semibold text-text">{int(s.n)}</b> new arXiv papers whose
					correct category is known: the one their authors chose. Jev picks the exact category for
					<b class="num font-semibold text-text">{pct(s.jev_accuracy, 1)}</b> of papers against <b class="num font-semibold text-text">{pct(s.llm_accuracy, 1)}</b>
					for {llm} ({pct(s.jev_lenient, 1)} vs {pct(s.llm_lenient, 1)} when any listed category counts). It answers in
					<b class="num font-semibold text-text">{ms(s.jev_p50_ms)}</b> at the median against {ms(s.llm_p50_ms)}, <b class="font-semibold text-text">{fmtTimes(times(s.jev_p50_ms, s.llm_p50_ms))} faster</b>,
					and costs {usd((s.jev_cost_per_paper ?? 0) * 1000)} per thousand papers against {usd((s.llm_cost_per_paper ?? 0) * 1000)},
					<b class="font-semibold text-text">{fmtTimes(times(s.jev_cost_per_paper, s.llm_cost_per_paper))} cheaper</b>.{#if sure?.accuracy != null}{' '}Acting only on answers it is at least 90% sure of, Jev sorts {pct(sure.coverage)} of papers at {pct(sure.accuracy, 1)} accuracy.{/if}
				{:else}
					We race Jev, a decision model that returns calibrated probabilities over a fixed set of answers, against a generative
					LLM on new arXiv papers whose correct category is known. Results appear here as soon as both models have judged the
					first papers: run <code class="font-mono text-sm">make benchmark N=200</code>.
				{/if}
			</p>
		</div>
	</header>

	<Pipeline />

	<section class="mt-14" aria-labelledby="results">
		<h2 id="results" class="section-head mb-4"><span class="n">1</span>Results</h2>
		<HeadToHead />
		<div class="mt-4 grid gap-4 lg:grid-cols-3">
			<CategoryChart />
			<div class="grid content-start gap-4"><ConfidenceCharts /></div>
			<div class="grid content-start gap-4"><LatencyChart /><Mistakes /></div>
		</div>
	</section>

	<section class="mt-14" aria-labelledby="submissions">
		<h2 id="submissions" class="section-head mb-4"><span class="n">2</span>Live submissions</h2>
		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
			<Feed />
			<aside class="lg:sticky lg:top-4 lg:self-start"><Race /></aside>
		</div>
	</section>

	<footer class="mt-16 border-t border-rule pt-3 text-xs text-muted">
		Data: arXiv API (metadata CC0). Ground truth: each paper's primary category, chosen by its authors. Costs use each
		response's real token counts at list prices. Source: github.com/kristor27/arxiv-classifier.
	</footer>
</div>
