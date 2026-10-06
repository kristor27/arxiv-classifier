<script lang="ts">
	import { ORDER, TOPICS, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import EditCard from './EditCard.svelte';

	const topics = $derived(
		(live.stats?.topic_names ?? Object.keys(TOPICS)).map((t) => {
			const row = live.stats?.topics.find((r) => r.topic === t);
			return { key: t, n: row?.n ?? 0, disruptive: row?.disruptive ?? 0 };
		})
	);
	const chip = 'shrink-0 rounded-full border px-2.5 py-1 text-xs transition';
	const on = 'border-jev bg-jev/10 text-jev';
	const off = 'border-border text-text-2 hover:border-muted';
</script>

<section class="flex min-h-0 flex-col">
	<div class="mb-3 flex flex-wrap items-center gap-2">
		<h2 class="mr-auto text-sm font-semibold">Live feed <span class="font-normal text-muted">· English Wikipedia</span></h2>
		<div class="flex rounded-lg bg-surface p-0.5 text-xs shadow-[var(--glow)]" role="tablist">
			{#each [null, ...ORDER] as v (v)}
				<button role="tab" aria-selected={live.filter.verdict === v} onclick={() => live.setFilter({ verdict: v })}
					class="rounded-md px-2.5 py-1 transition {live.filter.verdict === v ? 'bg-surface-2 font-medium text-text' : 'text-muted hover:text-text'}">
					{v ? VERDICTS[v].label : 'All'}
				</button>
			{/each}
		</div>
		<button onclick={() => live.toggleFreeze()} title="Freeze the list while you read; edits are still judged"
			class="rounded-lg bg-surface px-3 py-1.5 text-xs font-medium shadow-[var(--glow)] hover:bg-surface-2">
			{live.frozen ? `▶ Unfreeze${live.queued.length ? ` (${live.queued.length} new)` : ''}` : '❚❚ Freeze'}
		</button>
	</div>

	<!-- Topic filter: Jev answers "what is this article about?" in the same call as the verdict. -->
	<div class="mb-3 flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Filter by topic">
		<button role="tab" aria-selected={!live.filter.topic} onclick={() => live.setFilter({ topic: null })}
			class="{chip} {!live.filter.topic ? on : off}">All topics</button>
		{#each topics as t (t.key)}
			<button role="tab" aria-selected={live.filter.topic === t.key} onclick={() => live.setFilter({ topic: t.key })}
				class="{chip} {live.filter.topic === t.key ? on : off}"
				title="{t.n} edits, {t.disruptive} disruptive">
				{TOPICS[t.key] ?? t.key}
				<span class="num ml-1 text-muted">{t.n}</span>
				{#if t.disruptive}<span class="num ml-1 text-crit">{Math.round((t.disruptive / t.n) * 100)}%✕</span>{/if}
			</button>
		{/each}
	</div>

	<div class="grid gap-3">
		{#each live.edits as edit (edit.rev)}
			<div class="enter"><EditCard {edit} /></div>
		{:else}
			<p class="card p-8 text-center text-sm text-muted">
				{live.stats?.paused ? 'Judging is stopped. Press “Resume judging” at the top.' : 'Waiting for the next matching edit…'}
			</p>
		{/each}
	</div>
</section>

<style>
	/* Plays once when a card is mounted, i.e. when a new edit arrives. */
	.enter { animation: enter 0.45s cubic-bezier(0.2, 0.8, 0.2, 1); }
	@keyframes enter {
		from { opacity: 0; transform: translateY(-10px) scale(0.99); }
	}
</style>
