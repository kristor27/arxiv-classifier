<script lang="ts">
	import { ORDER, VERDICTS } from '$lib/format';
	import type { Verdict } from '$lib/types';

	// Jev's calibrated probabilities, drawn as one stacked bar with 2px gaps between segments.
	let { probs }: { probs: Record<Verdict, number> } = $props();
</script>

<div class="flex h-1.5 w-full gap-[2px] overflow-hidden rounded-full" role="img"
	aria-label={ORDER.map((v) => `${VERDICTS[v].label} ${Math.round(probs[v] * 100)}%`).join(', ')}>
	{#each ORDER as v (v)}
		{#if probs[v] > 0.005}
			<div class="h-full transition-[flex-grow] duration-700 first:rounded-l-full last:rounded-r-full"
				style="flex-grow: {probs[v]}; background: {VERDICTS[v].color}"
				title="{VERDICTS[v].label}: {Math.round(probs[v] * 100)}%"></div>
		{/if}
	{/each}
</div>
