<script lang="ts">
	import { onMount } from 'svelte';
	import { Tween } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';
	import Feed from '$lib/components/Feed.svelte';
	import LatencyChart from '$lib/components/LatencyChart.svelte';
	import Pipeline from '$lib/components/Pipeline.svelte';
	import PulseChart from '$lib/components/PulseChart.svelte';
	import Race from '$lib/components/Race.svelte';
	import { int, ms, ORDER, ratio, usd, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';

	onMount(() => live.start());

	const s = $derived(live.stats);
	const opts = { duration: 900, easing: cubicOut };
	const total = new Tween(0, opts);
	const jevCost = new Tween(0, opts);
	const llmCost = new Tween(0, opts);
	$effect(() => {
		if (!s) return;
		total.target = s.total;
		jevCost.target = s.jev_cost;
		llmCost.target = s.llm_cost_if_all ?? 0;
	});
	const llmName = $derived(s?.engines.llm ?? 'The LLM');
	const slower = $derived(ratio(s?.jev_p50_ms, s?.llm_p50_ms));
	const cheaper = $derived(ratio(s?.jev_cost_per_edit, s?.llm_cost_per_edit));
	const running = $derived(live.connected && !s?.paused);
	const precision = $derived(s && s.flagged_checked ? s.flagged_reverted / s.flagged_checked : null);

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

{#snippet tile(label: string, value: string, sub: string, accent = false)}
	<div class="card p-4">
		<p class="text-xs text-muted">{label}</p>
		<p class="num mt-1 text-2xl font-semibold tracking-tight {accent ? 'text-jev' : ''}">{value}</p>
		<p class="num mt-1 text-xs text-text-2">{sub}</p>
	</div>
{/snippet}

<div class="mx-auto max-w-[1400px] px-4 py-6 sm:px-6">
	<header class="mb-6 flex flex-wrap items-center gap-4">
		<div class="flex items-center gap-3">
			<svg viewBox="0 0 32 32" class="size-9" aria-hidden="true"><rect width="32" height="32" rx="9" fill="var(--surface)" stroke="var(--border)" /><path d="M4 17h6l3-8 5 15 3-7h7" fill="none" stroke="var(--jev)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
			<div>
				<h1 class="text-xl font-bold tracking-tight">WikiPulse</h1>
				<p class="text-xs text-text-2">An immune system for Wikipedia — every edit judged live by <b class="text-jev">Jev</b></p>
			</div>
		</div>
		<div class="ml-auto flex items-center gap-2 text-xs">
			<span class="inline-flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 shadow-[var(--glow)]">
				<span class="relative flex size-2">
					{#if running}<span class="absolute inline-flex size-full animate-ping rounded-full bg-good opacity-70"></span>{/if}
					<span class="relative inline-flex size-2 rounded-full {running ? 'bg-good' : s?.paused ? 'bg-warn' : 'bg-muted'}"></span>
				</span>
				{!live.connected ? 'Connecting…' : s?.paused ? 'Stopped' : 'Live'}
			</span>
			{#if s}
				<button onclick={() => live.setPaused(!s.paused)}
					class="rounded-full px-3 py-1.5 font-medium shadow-[var(--glow)] transition {s.paused ? 'bg-jev text-white hover:brightness-110' : 'bg-surface hover:bg-surface-2'}"
					title={s.paused ? 'Send new edits to Jev again' : 'Stop sending edits to Jev (and stop paying for it)'}>
					{s.paused ? '▶ Resume judging' : '■ Stop judging'}
				</button>
			{/if}
			<button onclick={toggleTheme} class="rounded-full bg-surface px-3 py-1.5 shadow-[var(--glow)] hover:bg-surface-2" aria-label="Toggle dark mode">◐</button>
			<a href="/api/docs" target="_blank" class="rounded-full bg-surface px-3 py-1.5 shadow-[var(--glow)] hover:bg-surface-2">API docs</a>
		</div>
	</header>

	<Pipeline />

	<div class="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
		{@render tile('Edits judged', int(total.current), s ? `${int(s.disruptive)} flagged disruptive` : '…')}
		{@render tile('Jev median response', ms(s?.jev_p50_ms), s?.llm_p50_ms ? `${llmName} ${ms(s.llm_p50_ms)} · ${slower}× slower` : `${llmName}: no samples yet`, true)}
		{@render tile('Spent on Jev so far', usd(jevCost.current), s?.llm_cost_if_all ? `${llmName} would have cost ${usd(llmCost.current)}` : `${llmName} cost: no samples yet`)}
		{@render tile('A year of all Wikimedia', usd(s?.jev_cost_per_year_all_wikimedia), s?.llm_cost_per_year_all_wikimedia ? `${llmName}: ${usd(s.llm_cost_per_year_all_wikimedia)} · ${cheaper}× more` : `${s ? s.all_wikimedia_edits_per_s.toFixed(1) : '…'} edits/s, every one judged`)}
		{@render tile('Confirmed by humans', precision == null ? '—' : `${Math.round(precision * 100)}%`,
			precision == null ? 'of flags reverted · first check after 30 min' : `of ${int(s!.flagged_checked)} disruptive flags were reverted`)}
	</div>

	<main class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
		<Feed />
		<aside class="grid content-start gap-4">
			<Race />
			<PulseChart />
			<LatencyChart />
			{#if s && s.total}
				<section class="card p-5">
					<h2 class="text-sm font-semibold">Verdict mix</h2>
					<div class="mt-3 flex h-2.5 gap-[2px] overflow-hidden rounded-full">
						{#each ORDER as v (v)}
							<div style="flex-grow: {s[v]}; background: {VERDICTS[v].color}" title="{VERDICTS[v].label}: {s[v]}"></div>
						{/each}
					</div>
					<ul class="mt-3 grid gap-1 text-xs">
						{#each ORDER as v (v)}
							<li class="flex items-center gap-2 text-text-2">
								<span class="size-2 rounded-sm" style="background: {VERDICTS[v].color}"></span>{VERDICTS[v].label}
								<span class="num ml-auto text-text">{int(s[v])}</span>
								<span class="num w-10 text-right text-muted">{Math.round((s[v] / s.total) * 100)}%</span>
							</li>
						{/each}
					</ul>
					{#if s.agreement != null}<p class="num mt-3 text-xs text-muted">Jev and {llmName} agree on {Math.round(s.agreement * 100)}% of {int(s.llm_n)} shared edits.</p>{/if}
				</section>
			{/if}
		</aside>
	</main>

	<footer class="mt-10 pb-4 text-center text-xs text-muted">
		Data: Wikimedia EventStreams (CC BY-SA). Verdicts by {s?.engines.jev ?? 'Jev'}; comparison by {s?.engines.llm ?? 'an LLM'} on a sample of edits.
	</footer>
</div>
