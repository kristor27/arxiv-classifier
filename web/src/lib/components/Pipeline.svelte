<script lang="ts">
	import { int, ms, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Verdict } from '$lib/types';

	// How the system works, animated: every real edit is a dot that changes color once Jev has judged it.
	const s = $derived(live.stats);
	const nodes = $derived([
		{ name: 'Wikipedia', sub: s ? `${s.all_wikimedia_edits_per_s.toFixed(1)} edits/s worldwide` : 'live stream' },
		{ name: 'Redis queue', sub: 'buffers the burst' },
		{ name: 'Jev', sub: s?.paused ? 'stopped' : s?.jev_p50_ms ? `${ms(s.jev_p50_ms)} per verdict` : 'judges', hero: !s?.paused },
		{ name: 'Postgres', sub: s ? `${int(s.total)} verdicts` : 'stores' },
		{ name: 'You', sub: live.connected ? 'live over WebSocket' : 'reconnecting…' }
	]);
</script>

<section class="card px-5 pt-4 pb-5" aria-label="How WikiPulse works">
	<p class="mb-4 text-xs font-medium tracking-wide text-muted uppercase">How it works · every dot is a real edit</p>
	<div class="relative">
		<div class="absolute top-[11px] right-[10%] left-[10%] h-[2px] bg-border"></div>
		{#each live.arrivals as a (a.id)}
			<span class="dot absolute top-[7px] size-2.5 rounded-full"
				style="--c: {VERDICTS[a.verdict as Verdict].color}"></span>
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
</section>

<style>
	.dot {
		left: 10%;
		background: var(--muted);
		animation: travel 2.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
	}
	/* Gray until it reaches Jev (the middle node), then it takes the verdict's color. */
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
