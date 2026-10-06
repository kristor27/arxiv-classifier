<script lang="ts">
	import { int } from '$lib/format';
	import { live } from '$lib/live.svelte';

	// How the system works, animated: every judged paper is a dot that turns green or red when it passes the judges.
	const s = $derived(live.stats);
	const nodes = $derived([
		{ name: 'arXiv', sub: 'new papers, polled' },
		{ name: 'Redis queue', sub: 'one paper per job' },
		{ name: `Jev + ${s?.engines.llm?.replace('Claude ', '') ?? 'LLM'}`, sub: s?.paused ? 'stopped' : 'judged at the same instant', hero: !s?.paused },
		{ name: 'Postgres', sub: s ? `${int(s.total)} papers scored` : 'scores' },
		{ name: 'You', sub: live.connected ? 'live over WebSocket' : 'reconnecting…' }
	]);
</script>

<figure class="card px-5 pt-5 pb-4" aria-label="How it works">
	<div class="relative">
		<div class="absolute top-[11px] right-[10%] left-[10%] h-[2px] bg-border"></div>
		{#each live.arrivals as a (a.id)}
			<span class="dot absolute top-[7px] size-2.5 rounded-full" style="--c: {a.ok ? 'var(--good)' : 'var(--crit)'}"></span>
		{/each}
		<ol class="relative grid grid-cols-5">
			{#each nodes as n (n.name)}
				<li class="flex flex-col items-center text-center">
					<span class="z-10 grid size-6 place-items-center rounded-full border-2 bg-surface
						{n.hero ? 'border-jev shadow-[0_0_0_4px_color-mix(in_oklab,var(--jev)_20%,transparent)]' : 'border-border'}">
						<span class="size-2 rounded-full {n.hero ? 'bg-jev' : 'bg-muted'}"></span>
					</span>
					<span class="mt-2 text-xs font-semibold sm:text-sm {n.hero ? 'text-jev' : ''}">{n.name}</span>
					<span class="num hidden text-[11px] text-muted sm:block">{n.sub}</span>
				</li>
			{/each}
		</ol>
	</div>
	<figcaption class="caption mt-4"><b>Figure 1.</b>Method. Every dot is a real paper travelling through the system; it turns green when Jev picks the right category and red when it doesn't.</figcaption>
</figure>

<style>
	.dot { left: 10%; background: var(--muted); animation: travel 2.4s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
	/* Grey until it reaches the judges (the middle node), then green (Jev right) or red (Jev wrong). */
	@keyframes travel {
		0% { left: 10%; opacity: 0; background: var(--muted); }
		8% { opacity: 1; }
		48% { background: var(--muted); transform: scale(1); }
		52% { background: var(--c); transform: scale(1.8); }
		60% { transform: scale(1); }
		92% { opacity: 1; }
		100% { left: calc(90% - 10px); opacity: 0; background: var(--c); }
	}
</style>
