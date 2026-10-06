<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>WikiPulse — an immune system for Wikipedia</title>
	<meta name="description" content="Every English Wikipedia edit, judged live by Jev." />
</svelte:head>

{@render children()}
