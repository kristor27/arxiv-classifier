<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Jev vs LLM on arXiv</title>
	<meta name="description" content="A live evaluation: Jev against a generative LLM, sorting new arXiv papers." />
</svelte:head>

{@render children()}
