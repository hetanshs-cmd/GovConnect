import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, Sparkles } from 'lucide-react';

interface Message {
	id: string;
	text: string;
	sender: 'user' | 'bot';
	timestamp: Date;
	status?: 'sending' | 'sent' | 'error';
}

interface ChatBoxProps {
	isDark: boolean;
}

const ChatBox: React.FC<ChatBoxProps> = ({ isDark }) => {
	const [isOpen, setIsOpen] = useState(false);
	const [messages, setMessages] = useState<Message[]>([
		{
			id: '1',
			text: 'Hey there! 👋 I\'m GovConnect Assistant, your friendly guide to government services. I\'m here to help with healthcare, agriculture, and urban services. What can I help you with today?',
			sender: 'bot',
			timestamp: new Date(),
			status: 'sent'
		}
	]);
	const [inputMessage, setInputMessage] = useState('');
	const [dimensions, setDimensions] = useState({ width: 350, height: 450 });
	const [isResizing, setIsResizing] = useState(false);
	const [resizeStart, setResizeStart] = useState({ x: 0, y: 0 });
	const [isLoading, setIsLoading] = useState(false);
	const [isTyping, setIsTyping] = useState(false);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);
	const chatWindowRef = useRef<HTMLDivElement>(null);

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	};

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	useEffect(() => {
		if (isOpen && inputRef.current) {
			inputRef.current.focus();
		}
	}, [isOpen]);

	// Resize functionality
	useEffect(() => {
		const handleMouseMove = (e: MouseEvent) => {
			if (!isResizing || !chatWindowRef.current) return;

			const deltaX = e.clientX - resizeStart.x;
			const deltaY = e.clientY - resizeStart.y;

			const newWidth = Math.max(320, Math.min(600, dimensions.width + deltaX));
			const newHeight = Math.max(350, Math.min(700, dimensions.height + deltaY));

			setDimensions({ width: newWidth, height: newHeight });
			setResizeStart({ x: e.clientX, y: e.clientY });
		};

		const handleMouseUp = () => {
			setIsResizing(false);
			document.body.style.cursor = '';
			document.body.style.userSelect = '';
		};

		if (isResizing) {
			document.addEventListener('mousemove', handleMouseMove);
			document.addEventListener('mouseup', handleMouseUp);
		}

		return () => {
			document.removeEventListener('mousemove', handleMouseMove);
			document.removeEventListener('mouseup', handleMouseUp);
		};
	}, [isResizing, resizeStart, dimensions]);

	const handleResizeStart = (e: React.MouseEvent) => {
		e.preventDefault();
		setIsResizing(true);
		setResizeStart({ x: e.clientX, y: e.clientY });
		document.body.style.cursor = 'nw-resize';
		document.body.style.userSelect = 'none';
	};

	const handleSendMessage = async () => {
		if (inputMessage.trim() && !isLoading) {
			const newMessage: Message = {
				id: Date.now().toString(),
				text: inputMessage.trim(),
				sender: 'user',
				timestamp: new Date(),
				status: 'sending'
			};

			setMessages(prev => [...prev, newMessage]);
			setInputMessage('');
			setIsLoading(true);
			setIsTyping(true);

			try {
				const response = await fetch('/api/chat', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					credentials: 'include',
					body: JSON.stringify({ message: newMessage.text }),
				});

				if (response.ok) {
					const data = await response.json();
					const botResponse: Message = {
						id: (Date.now() + 1).toString(),
						text: data.response,
						sender: 'bot',
						timestamp: new Date(data.timestamp),
						status: 'sent'
					};

					// Update user message status
					setMessages(prev => prev.map(msg =>
						msg.id === newMessage.id ? { ...msg, status: 'sent' } : msg
					));

					// Add bot response with typing delay for better UX
					setTimeout(() => {
						setMessages(prev => [...prev, botResponse]);
						setIsTyping(false);
					}, 500);
				} else {
					throw new Error('API response not ok');
				}
			} catch (error) {
				console.error('Chat API error:', error);
				const errorMessage: Message = {
					id: (Date.now() + 1).toString(),
					text: 'Sorry, I\'m having trouble connecting right now. Please check your connection and try again.',
					sender: 'bot',
					timestamp: new Date(),
					status: 'error'
				};

				// Update user message status to error
				setMessages(prev => prev.map(msg =>
					msg.id === newMessage.id ? { ...msg, status: 'error' } : msg
				));

				setMessages(prev => [...prev, errorMessage]);
				setIsTyping(false);
			} finally {
				setIsLoading(false);
			}
		}
	};

	const handleKeyPress = (e: React.KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSendMessage();
		}
	};

	const toggleChat = () => {
		setIsOpen(!isOpen);
	};

	return (
		<>
			{/* Enhanced Chat Toggle Button */}
			<button
				onClick={toggleChat}
				className={`fixed bottom-6 right-6 z-50 p-4 rounded-full shadow-xl transition-all duration-300 hover:scale-110 group ${isDark
					? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-blue-500/25'
					: 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 text-white shadow-blue-500/25'
					}`}
				aria-label="Open GovConnect Assistant"
			>
				<div className="relative">
					<MessageCircle size={24} />
					<div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
					<div className="absolute inset-0 rounded-full bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
				</div>
			</button>

			{/* Enhanced Chat Window */}
			{isOpen && (
				<div
					ref={chatWindowRef}
					className={`fixed z-40 rounded-2xl shadow-2xl transition-all duration-300 backdrop-blur-sm ${isDark
						? 'bg-gray-900/95 border border-gray-700/50 shadow-gray-900/50'
						: 'bg-white/95 border border-gray-200/50 shadow-gray-900/10'
						} backdrop-filter`}
					style={{
						bottom: '100px',
						right: '24px',
						width: `${dimensions.width}px`,
						height: `${dimensions.height}px`,
						minWidth: '320px',
						minHeight: '350px'
					}}
				>
					{/* Resize Handle */}
					<div
						className="absolute bottom-0 right-0 w-6 h-6 cursor-nw-resize opacity-0 hover:opacity-100 transition-opacity rounded-tl-md"
						onMouseDown={handleResizeStart}
						style={{
							background: `linear-gradient(-45deg, transparent 0%, transparent 40%, ${isDark ? 'rgba(75, 85, 99, 0.8)' : 'rgba(156, 163, 175, 0.8)'} 40%, ${isDark ? 'rgba(75, 85, 99, 0.8)' : 'rgba(156, 163, 175, 0.8)'} 60%, transparent 60%, transparent 100%)`
						}}
					/>

					{/* Enhanced Chat Header */}
					<div
						className={`flex items-center justify-between p-4 border-b rounded-t-2xl ${isDark
							? 'border-gray-700/50 bg-gradient-to-r from-gray-800 to-gray-900'
							: 'border-gray-200/50 bg-gradient-to-r from-gray-50 to-white'
							}`}
					>
						<div className="flex items-center space-x-3">
							<div className={`p-2 rounded-full ${isDark ? 'bg-blue-600/20' : 'bg-blue-500/20'}`}>
								<Bot size={20} className={isDark ? 'text-blue-400' : 'text-blue-600'} />
							</div>
							<div>
								<h3 className={`font-semibold text-lg ${isDark ? 'text-white' : 'text-gray-900'}`}>
									GovConnect Assistant
								</h3>
								<p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
									AI-powered government services
								</p>
							</div>
						</div>
						<div className="flex items-center space-x-2">
							<div className="flex items-center space-x-1">
								<div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
								<span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Online</span>
							</div>
							<button
								onClick={toggleChat}
								className={`p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'
									}`}
								aria-label="Close chat"
							>
								<X size={18} />
							</button>
						</div>
					</div>

					{/* Enhanced Chat Content */}
					<div
						className={`flex-1 overflow-y-auto p-4 space-y-4 ${isDark ? 'bg-gray-900/50' : 'bg-gray-50/50'
							}`}
						style={{ height: `calc(${dimensions.height}px - 140px)` }}
					>
						{messages.map((message) => (
							<div
								key={message.id}
								className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
							>
								<div
									className={`flex items-start space-x-3 max-w-xs lg:max-w-md ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
								>
									{/* Avatar */}
									<div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.sender === 'user'
										? isDark ? 'bg-blue-600' : 'bg-blue-500'
										: isDark ? 'bg-gray-700' : 'bg-gray-200'
										}`}>
										{message.sender === 'user' ? (
											<User size={16} className="text-white" />
										) : (
											<Bot size={16} className={isDark ? 'text-gray-300' : 'text-gray-600'} />
										)}
									</div>

									{/* Message Bubble */}
									<div
										className={`relative px-4 py-3 rounded-2xl shadow-sm ${message.sender === 'user'
											? isDark
												? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
												: 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white'
											: isDark
												? 'bg-gray-700 text-gray-100 border border-gray-600'
												: 'bg-white text-gray-900 border border-gray-200'
											}`}
									>
										<p className="text-sm leading-relaxed">{message.text}</p>

										{/* Message Status */}
										{message.sender === 'user' && message.status && (
											<div className="flex items-center justify-end mt-2 space-x-1">
												<span className={`text-xs ${message.sender === 'user' ? 'text-blue-100' : isDark ? 'text-gray-400' : 'text-gray-500'}`}>
													{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
												</span>
												{message.status === 'sending' && (
													<div className="flex space-x-1">
														<div className="w-1 h-1 bg-blue-200 rounded-full animate-bounce"></div>
														<div className="w-1 h-1 bg-blue-200 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
														<div className="w-1 h-1 bg-blue-200 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
													</div>
												)}
												{message.status === 'sent' && (
													<div className="w-3 h-3 text-blue-200">✓</div>
												)}
												{message.status === 'error' && (
													<div className="w-3 h-3 text-red-400">⚠</div>
												)}
											</div>
										)}

										{message.sender === 'bot' && (
											<div className="flex items-center justify-end mt-2">
												<span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
													{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
												</span>
											</div>
										)}
									</div>
								</div>
							</div>
						))}

						{/* Typing Indicator */}
						{isTyping && (
							<div className="flex justify-start">
								<div className="flex items-start space-x-3">
									<div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
										<Bot size={16} className={isDark ? 'text-gray-300' : 'text-gray-600'} />
									</div>
									<div className={`px-4 py-3 rounded-2xl ${isDark ? 'bg-gray-700 border border-gray-600' : 'bg-white border border-gray-200'}`}>
										<div className="flex space-x-1">
											<div className="flex space-x-1">
												<div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
												<div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
												<div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
											</div>
											<span className={`text-xs ml-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Typing...</span>
										</div>
									</div>
								</div>
							</div>
						)}

						<div ref={messagesEndRef} />
					</div>

					{/* Enhanced Input Area */}
					<div
						className={`p-4 border-t rounded-b-2xl ${isDark
							? 'border-gray-700/50 bg-gradient-to-r from-gray-800 to-gray-900'
							: 'border-gray-200/50 bg-gradient-to-r from-gray-50 to-white'
							}`}
					>
						<div className="flex space-x-3">
							<div className="flex-1 relative">
								<input
									ref={inputRef}
									type="text"
									value={inputMessage}
									onChange={(e) => setInputMessage(e.target.value)}
									onKeyPress={handleKeyPress}
									placeholder="What's on your mind? Ask me anything! 💬"
									className={`w-full px-4 py-3 pr-12 text-sm border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all ${isDark
										? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:bg-gray-600'
										: 'bg-white border-gray-300 text-gray-900 placeholder-gray-500 focus:bg-gray-50'
										}`}
									disabled={isLoading}
								/>
								{inputMessage.trim() && (
									<div className="absolute right-3 top-1/2 transform -translate-y-1/2">
										<Sparkles size={16} className={isDark ? 'text-blue-400' : 'text-blue-500'} />
									</div>
								)}
							</div>
							<button
								onClick={handleSendMessage}
								disabled={!inputMessage.trim() || isLoading}
								className={`p-3 rounded-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none ${inputMessage.trim() && !isLoading
									? isDark
										? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/25'
										: 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 text-white shadow-lg shadow-blue-500/25'
									: isDark
										? 'bg-gray-700 text-gray-500 cursor-not-allowed'
										: 'bg-gray-200 text-gray-400 cursor-not-allowed'
									}`}
								aria-label="Send message"
							>
								{isLoading ? (
									<div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
								) : (
									<Send size={18} />
								)}
							</button>
						</div>

						{/* Quick Suggestions */}
						<div className="flex flex-wrap gap-2 mt-3">
							{["I need to book a doctor appointment", "How do I register as a farmer?", "I want to report an issue"].map((suggestion) => (
								<button
									key={suggestion}
									onClick={() => setInputMessage(suggestion)}
									className={`px-3 py-1 text-xs rounded-full border transition-colors ${isDark
										? 'border-gray-600 text-gray-300 hover:border-gray-500 hover:text-gray-200'
										: 'border-gray-300 text-gray-600 hover:border-gray-400 hover:text-gray-700'
										}`}
								>
									{suggestion}
								</button>
							))}
						</div>
					</div>
				</div>
			)}
		</>
	);
};

export default ChatBox;